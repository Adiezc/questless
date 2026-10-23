# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Contract generation, funding, escrow and lifecycle.

Each tick, after the market clears:
1. ``expire_and_cancel``: live contracts past their deadline expire; untaken contracts whose need
   has gone away are withdrawn. Either way escrow is refunded and the need key cools down.
2. ``generate``: persistent needs become candidates. Guild emergencies (many members short of the
   same good) are pooled first, then transport bottlenecks, then individual needs by severity.
   Each candidate must pass: not a duplicate, not cooling down, under the caps, feasible, and
   funded. The reward is escrowed before the contract is posted, so an unfunded contract cannot
   exist. Every rejection is counted by reason.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from questless.contracts.causes import build_chain
from questless.contracts.model import Contract, ContractKind, Status
from questless.contracts.needs import TRANSPORT, NeedState
from questless.contracts.provenance import Evidence, Provenance
from questless.contracts.validation import obtainable, site_backlog
from questless.sim.alloc import allocate
from questless.sim.entities import ESCROW, PLAYER, TOWN, Profession, guild_account
from questless.sim.ledger import Asset
from questless.sim.market import budget, stock_target

if TYPE_CHECKING:
    from questless.sim.world import World


OUTCOME_DAYS = 7


def _outcome_snapshot(world: World, c: Contract) -> dict:
    """Beneficiaries' last ``OUTCOME_DAYS``: units produced, idle days, days short of the good;
    plus the market's unfilled demand for the good."""
    produced = idle = short = 0
    for npc_id in c.beneficiaries:
        for rec in list(world.npcs[npc_id].history)[-OUTCOME_DAYS:]:
            produced += sum(rec.produced.values())
            idle += rec.idle
            short += rec.unmet.get(c.good, 0) > 0
    window = world.stats[-OUTCOME_DAYS:]
    return {
        "tick": world.tick,
        "produced": produced,
        "idle_days": idle,
        "days_short": short,
        "market_unfilled": sum(s.market[c.good].unfilled for s in window if c.good in s.market),
    }


def adjust_reputation(world: World, c: Contract, delta: int) -> None:
    """Reputation with the guild behind the contract (the requester's guild), clamped to +-100."""
    if c.requester.startswith("guild:"):
        gid = c.requester.removeprefix("guild:")
    elif c.requester in world.npcs:
        gid = world.npcs[c.requester].guild_id
    else:
        gid = None
    guild = world.guilds.get(gid) if gid else None
    if guild is not None and c.accepted_by:
        rep = guild.reputation.get(c.accepted_by, 0) + delta
        guild.reputation[c.accepted_by] = max(-100, min(100, rep))


@dataclass(slots=True)
class Candidate:
    kind: ContractKind
    requester: str
    good: Asset
    beneficiaries: dict[str, int]
    needs: list[NeedState]
    guild_id: str | None = None
    # For an individual need: the pooled contract key that would cover it. The individual
    # contract is skipped only if that pooled contract is actually live.
    covered_by: tuple[str, str, str] | None = None

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.requester, str(self.kind), str(self.good))


@dataclass(slots=True)
class ContractTickReport:
    created: list[str] = field(default_factory=list)
    closed: list[str] = field(default_factory=list)
    suppressed: Counter[str] = field(default_factory=Counter)
    live: int = 0


@dataclass
class ContractBoard:
    contracts: dict[str, Contract] = field(default_factory=dict)
    cooldowns: dict[tuple[str, str, str], int] = field(default_factory=dict)  # key -> until tick
    next_id: int = 1

    def live(self) -> list[Contract]:
        return [c for c in self.contracts.values() if c.live]

    def live_for(self, key: tuple[str, str, str]) -> Contract | None:
        return next((c for c in self.live() if c.dedup_key == key), None)

    def ancestors(self, contract_id: str) -> list[str]:
        """Quest lineage upwards: parent, grandparent, ... (oldest last)."""
        out: list[str] = []
        parent = self.contracts[contract_id].parent_id
        while parent is not None and parent not in out:
            out.append(parent)
            parent = self.contracts[parent].parent_id
        return out

    def children(self, contract_id: str) -> list[str]:
        return sorted(c.id for c in self.contracts.values() if c.parent_id == contract_id)

    def step(self, world: World) -> ContractTickReport:
        report = ContractTickReport()
        self.expire_and_cancel(world, report)
        self.generate(world, report)
        self.measure_outcomes(world)
        report.live = len(self.live())
        return report

    # --- lifecycle ------------------------------------------------------------------------------

    def expire_and_cancel(self, world: World, report: ContractTickReport) -> None:
        resolve_days = world.config.contracts.resolve_days
        for c in sorted(self.live(), key=lambda c: c.id):
            if world.tick >= c.deadline_tick:
                self._close(world, c, Status.EXPIRED, report)
            elif c.status is Status.OPEN and _need_resolved(world, c, resolve_days):
                self._close(world, c, Status.CANCELLED, report)

    def _close(self, world: World, c: Contract, status: Status, report: ContractTickReport) -> None:
        world.ledger.transfer(
            ESCROW, c.funder, Asset.COIN, c.reward, tick=world.tick, reason=f"refund {c.id}"
        )
        if c.status is Status.ACCEPTED:  # the player took it and let it lapse
            adjust_reputation(world, c, -c.rep_reward)
        c.status = status
        c.closed_tick = world.tick
        self.cooldowns[c.dedup_key] = world.tick + world.config.contracts.cooldown_days
        report.closed.append(c.id)

    def accept(self, world: World, contract_id: str, player: str) -> Contract:
        c = self.contracts[contract_id]
        if c.status is not Status.OPEN:
            raise ValueError(f"{contract_id} is {c.status}, not open")
        c.status = Status.ACCEPTED
        c.accepted_by = player
        return c

    def fulfil(self, world: World, contract_id: str, player: str) -> Contract:
        """Deliver the contract from ``player``'s holdings and pay out the escrowed reward."""
        c = self.contracts[contract_id]
        if c.status is not Status.ACCEPTED or c.accepted_by != player:
            raise ValueError(f"{contract_id} is not accepted by {player}")
        if world.tick >= c.deadline_tick:
            raise ValueError(f"{contract_id} is past its deadline")
        if c.kind is ContractKind.TRANSPORT:
            for npc_id, qty in sorted(c.beneficiaries.items()):
                npc = world.npcs[npc_id]
                haul = min(qty, world.ledger.balance(npc.site_account, c.good))
                world.ledger.transfer(
                    npc.site_account, npc.account, c.good, haul, tick=world.tick, reason=c.id
                )
        else:
            if world.ledger.balance(player, c.good) < c.qty:
                raise ValueError(f"{player} holds fewer than {c.qty} {c.good}")
            for npc_id, qty in sorted(c.beneficiaries.items()):
                world.ledger.transfer(player, npc_id, c.good, qty, tick=world.tick, reason=c.id)
        world.ledger.transfer(ESCROW, player, Asset.COIN, c.reward, tick=world.tick, reason=c.id)
        c.status = Status.FULFILLED
        c.closed_tick = world.tick
        c.outcome = {"before": _outcome_snapshot(world, c), "after": None}
        return c

    def measure_outcomes(self, world: World) -> None:
        """``OUTCOME_DAYS`` after delivery, record what changed for the beneficiaries."""
        for c in self.contracts.values():
            if (
                c.status is Status.FULFILLED
                and c.outcome.get("after") is None
                and world.tick - c.closed_tick + 1 >= OUTCOME_DAYS  # days simulated since
            ):
                c.outcome["after"] = _outcome_snapshot(world, c)

    # --- generation -----------------------------------------------------------------------------

    def generate(self, world: World, report: ContractTickReport) -> None:
        cfg = world.config.contracts
        for cand in _candidates(world, self):
            if cand.covered_by:
                live_pool = self.live_for(cand.covered_by)
                if live_pool and live_pool.beneficiaries.get(cand.requester, 0) > 0:
                    report.suppressed["covered_by_pool"] += 1
                    continue
            if self.live_for(cand.key):
                report.suppressed["duplicate"] += 1
                continue
            if self.cooldowns.get(cand.key, -1) > world.tick:
                report.suppressed["cooldown"] += 1
                continue
            if len(self.live()) >= cfg.max_open:
                report.suppressed["cap_reached"] += 1
                continue
            if len(report.created) >= cfg.max_new_per_tick:
                report.suppressed["rate_limited"] += 1
                continue
            contract = self._try_post(world, cand, report)
            if contract:
                report.created.append(contract.id)

    def _try_post(
        self, world: World, cand: Candidate, report: ContractTickReport
    ) -> Contract | None:
        cfg = world.config.contracts
        price = world.unit_price(cand.good)
        wanted = sum(cand.beneficiaries.values())
        if cand.kind is ContractKind.TRANSPORT:
            feasible = wanted  # bounded by the backlog by construction
            unit_value = price * world.config.transport.fee_rate  # the haulage, not the goods
        else:
            feasible = min(wanted, obtainable(world, cand.good, exclude=set(cand.beneficiaries)))
            unit_value = price
        if feasible <= 0:
            report.suppressed["infeasible"] += 1
            return None

        funding = _choose_funder(world, cand, unit_value * _urgency(world, cand), feasible)
        if funding is None:
            report.suppressed["unfunded"] += 1
            return None
        funder, premium, cap, qty = funding
        if funder.startswith("guild:"):
            # Guilds pay a trusted player up to 10% more and a distrusted one up to 10% less.
            rep = world.guilds[funder.removeprefix("guild:")].reputation.get(PLAYER, 0)
            premium = max(premium * (1 + rep / 1000), 1.0)
        # Premium and urgency are >= 1, so the reward always covers at least market value.
        reward = max(min(round(qty * unit_value * premium * _urgency(world, cand)), cap), 1)
        if reward < cfg.min_reward:
            report.suppressed["too_small"] += 1
            return None
        beneficiaries = {
            k: v for k, v in allocate(qty, sorted(cand.beneficiaries.items())).items() if v > 0
        }
        world.ledger.transfer(
            funder, ESCROW, Asset.COIN, reward, tick=world.tick, reason="contract escrow"
        )

        cid = f"C-{self.next_id:04d}"
        self.next_id += 1
        chain, parent = build_chain(
            world, cand, _evidence(world, cand, funder, reward, cap, qty, wanted)
        )
        contract = Contract(
            id=cid,
            kind=cand.kind,
            requester=cand.requester,
            funder=funder,
            good=cand.good,
            qty=qty,
            beneficiaries=beneficiaries,
            reward=reward,
            rep_reward=10 if cand.guild_id else 5,
            created_tick=world.tick,
            deadline_tick=world.tick + max(cfg.deadline_days, cfg.caravan_days + 2),
            dedup_key=cand.key,
            provenance=Provenance(
                chain=tuple(chain), world_hash=world.state_hash(), parent_contract=parent
            ),
            reason=_reason(world, cand, qty),
            parent_id=parent,
        )
        self.contracts[cid] = contract
        return contract


# --- candidates ---------------------------------------------------------------------------------


def _candidates(world: World, board: ContractBoard) -> list[Candidate]:
    needs = world.needs.persistent(world)
    covered: dict[tuple[str, Asset], tuple[str, str, str]] = {}
    pooled_cands: list[Candidate] = []
    for kind, account, members, threshold, gid in _pooling_bodies(world):
        # A guild (or the town, for its guards) acts on the share of members *currently* short
        # of a good, as soon as at least one of them has run out of patience.
        trigger_goods = sorted({s.good for s in needs if s.subject in members})
        for good in trigger_goods:
            states = world.needs.active_for(members, good)
            for state in states:
                covered[(state.subject, good)] = (account, str(kind), str(good))
            # Share among members who use the good at all (farmers, not merchants, need tools).
            if len(states) / max(len(_users(world, members, good)), 1) >= threshold:
                pooled_cands.append(
                    Candidate(
                        kind,
                        account,
                        good,
                        {s.subject: _shortfall(world, s.subject, good) for s in states},
                        states,
                        gid,
                    )
                )

    transport_cands = []
    for state in needs:
        if state.subject == TRANSPORT:
            backlog = site_backlog(world, state.good)
            owners_guild = {world.npcs[n].guild_id for n in backlog}
            gid = owners_guild.pop() if len(owners_guild) == 1 else None
            requester = guild_account(gid) if gid else TOWN
            transport_cands.append(
                Candidate(ContractKind.TRANSPORT, requester, state.good, backlog, [state], gid)
            )

    individual = [
        Candidate(
            ContractKind.PROCUREMENT,
            s.subject,
            s.good,
            {s.subject: _shortfall(world, s.subject, s.good)},
            [s],
            world.npcs[s.subject].guild_id,
            covered_by=covered.get((s.subject, s.good)),
        )
        for s in needs
        if s.subject != TRANSPORT
    ]
    individual.sort(key=lambda c: (-c.needs[0].days * c.needs[0].unmet, c.requester, c.good))
    return pooled_cands + transport_cands + individual


def _users(world: World, members: list[str], good: Asset) -> list[str]:
    return [m for m in members if stock_target(world, world.npcs[m], good) > 0]


def _pooling_bodies(world: World) -> list[tuple[ContractKind, str, list[str], float, str | None]]:
    """Organisations that pool members' needs: each guild, and the town for its guards."""
    bodies: list[tuple[ContractKind, str, list[str], float, str | None]] = [
        (ContractKind.GUILD_SUPPLY, g.account, g.members, g.policy.emergency_threshold, gid)
        for gid, g in sorted(world.guilds.items())
        if g.members
    ]
    guards = [n.id for n in world.npcs_by_profession(Profession.GUARD)]
    if guards:
        threshold = world.config.contracts.town_emergency_threshold
        bodies.append((ContractKind.TOWN_SUPPLY, TOWN, guards, threshold, None))
    return bodies


def _shortfall(world: World, npc_id: str, good: Asset) -> int:
    npc = world.npcs[npc_id]
    return max(stock_target(world, npc, good) - world.ledger.balance(npc.account, good), 1)


# --- funding ------------------------------------------------------------------------------------


def _choose_funder(
    world: World, cand: Candidate, unit_cost: float, qty: int
) -> tuple[str, float, int, int] | None:
    """Pick who pays: (account, premium, max escrow, units funded).

    Options are tried in order (the NPC itself, then its guild, then the town for guards). The
    first that can fund every unit wins; otherwise the option funding the most units, so a guild
    that cannot cover a whole emergency still posts what it can afford. None if nobody can fund
    a single unit."""
    cfg = world.config.contracts
    guild = world.guilds.get(cand.guild_id) if cand.guild_id else None
    if guild is not None:
        guild_cap = int(
            world.ledger.balance(guild.account, Asset.COIN) * guild.policy.max_contract_share
        )
        guild_option = (guild.account, guild.policy.reward_premium, guild_cap)
    else:
        guild_option = None
    town_cap = int(world.ledger.balance(TOWN, Asset.COIN) * cfg.town_max_share)

    options: list[tuple[str, float, int]] = []
    if cand.kind is ContractKind.PROCUREMENT:
        npc = world.npcs[cand.requester]
        options.append((npc.account, cfg.npc_premium, budget(world, npc, cand.good)))
        if guild_option:
            options.append(guild_option)
        elif npc.profession is Profession.GUARD:
            options.append((TOWN, cfg.npc_premium, town_cap))
    elif guild_option:
        options.append(guild_option)
    elif cand.requester == TOWN:
        options.append((TOWN, cfg.npc_premium, town_cap))

    best: tuple[str, float, int, int] | None = None
    for account, premium, cap in options:
        units = min(qty, int(cap // (unit_cost * premium))) if unit_cost > 0 else qty
        if units == qty:
            return account, premium, cap, units
        if units > 0 and (best is None or units > best[3]):
            best = (account, premium, cap, units)
    return best


def _urgency(world: World, cand: Candidate) -> float:
    cfg = world.config.contracts
    overdue = max(
        s.days - (2 if s.subject == TRANSPORT else world.npcs[s.subject].traits.patience)
        for s in cand.needs
    )
    return min(1 + cfg.urgency_step * max(overdue, 0), cfg.max_urgency)


# --- contract-level evidence (root causes are prepended by causes.build_chain) -------------------


def _evidence(
    world: World, cand: Candidate, funder: str, reward: int, cap: int, qty: int, wanted: int
) -> list[Evidence]:
    t = world.tick
    good = cand.good
    market = world.stats[-1].market[good]
    chain: list[Evidence] = [
        Evidence(
            t,
            "unfilled_demand",
            f"market:{good}",
            "unfilled_units",
            market.unfilled,
            0,
            measure=(("unfilled", str(good)), t),
        )
    ]
    if cand.kind is ContractKind.TRANSPORT:
        backlog = sum(cand.beneficiaries.values())
        chain.append(Evidence(t, "transport_backlog", f"sites:{good}", "units_waiting", backlog))
    else:
        # Cite the member whose patience ran out (the trigger), longest streak first.
        def overdue(s: NeedState) -> tuple[bool, int, str]:
            return (s.days >= world.npcs[s.subject].traits.patience, s.days, s.subject)

        longest = max(cand.needs, key=overdue)
        patience = world.npcs[longest.subject].traits.patience
        chain.append(
            Evidence(
                longest.since,
                "need_persisted",
                longest.subject,
                f"days_without_{good}",
                longest.days,
                threshold=patience,
                caused_by=(0,),
            )
        )
    if cand.kind in (ContractKind.GUILD_SUPPLY, ContractKind.TOWN_SUPPLY):
        _, account, members, threshold, _ = next(
            b for b in _pooling_bodies(world) if b[1] == cand.requester
        )
        chain.append(
            Evidence(
                t,
                "guild_emergency" if cand.kind is ContractKind.GUILD_SUPPLY else "town_emergency",
                account,
                f"share_of_{cand.good}_users_affected",
                round(len(cand.needs) / len(_users(world, members, cand.good)), 3),
                threshold=threshold,
                caused_by=(1,),
            )
        )
    if qty < wanted:
        chain.append(
            Evidence(
                t,
                "partial_funding",
                funder,
                "units_funded",
                qty,
                threshold=wanted,
                caused_by=(len(chain) - 1,),
            )
        )
    chain.append(
        Evidence(
            t,
            "funding_decision",
            funder,
            "escrowed_coin",
            reward,
            threshold=cap,
            baseline=world.ledger.balance(funder, Asset.COIN) + reward,
            caused_by=(len(chain) - 1,),
        )
    )
    return chain


def _reason(world: World, cand: Candidate, qty: int) -> str:
    good = str(cand.good).replace("_", " ")
    if cand.kind is ContractKind.GUILD_SUPPLY:
        guild = world.guilds[cand.guild_id]
        users = len(_users(world, guild.members, cand.good))
        return (
            f"{guild.name}: {len(cand.needs)} of {users} members who use {good} cannot get it; "
            f"deliver {qty} {good}."
        )
    if cand.kind is ContractKind.TOWN_SUPPLY:
        guards = len(world.npcs_by_profession(Profession.GUARD))
        return f"Town Watch: {len(cand.needs)} of {guards} guards cannot get {good}; deliver {qty}."
    if cand.kind is ContractKind.TRANSPORT:
        return f"{qty} {good} stuck at production sites while the market runs short; haul it."
    npc = world.npcs[cand.requester]
    days = cand.needs[0].days
    return f"{npc.name} ({npc.profession}) has gone {days} days without {good}; deliver {qty}."


def _need_resolved(world: World, c: Contract, resolve_days: int) -> bool:
    if c.kind is ContractKind.TRANSPORT:
        return world.needs.calm_days(TRANSPORT, c.good) >= resolve_days
    recipients = [n for n, q in c.beneficiaries.items() if q > 0]
    return all(world.needs.calm_days(n, c.good) >= resolve_days for n in recipients)
