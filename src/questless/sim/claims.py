# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Land and mine claims (M60): work rights that earn rent, so wealth can earn more wealth.

Every gatherer works one claim at their site and, at genesis, owns it. Each day, after the market
clears:

1. ``collect_rent``: a worker who doesn't own their claim pays the owner ``rent_share`` of the
   day's output value, in coin, never going below ``rent_floor`` (the rest is forgiven).
2. ``trade``: an owner short of coin sells one claim to the richest NPC who can afford it and
   still keep ``buy_reserve``, and goes on working it as a tenant.

All coin moves on the ledger, so conservation holds; ``check`` verifies that every claim has one
owner and one worker.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from math import ceil
from statistics import fmean
from typing import TYPE_CHECKING

from questless.sim.ledger import Asset

if TYPE_CHECKING:
    from questless.sim.entities import DailyRecord
    from questless.sim.world import World

PRICE_WINDOW = 7  # days of output a claim's price is based on
RENT_CARRY = "rent"  # npc.carry key: rent fractions owed but not yet whole coins


@dataclass
class Claim:
    id: str  # e.g. "mine-03"
    site: str
    owner: str  # NPC id
    worker: str  # NPC id
    output_value: deque[float] = field(default_factory=lambda: deque(maxlen=PRICE_WINDOW))


@dataclass
class ClaimsReport:
    rent_paid: int = 0
    rent_unpaid: int = 0
    sold: int = 0
    sale_value: int = 0
    top10_share: float = 0.0  # share of claims owned by the richest 10% of NPCs, end of day
    paid_by: Counter[str] = field(default_factory=Counter)
    received_by: Counter[str] = field(default_factory=Counter)


def genesis(world: World) -> dict[str, Claim]:
    """One claim per gatherer, owned by the gatherer who works it."""
    claims: dict[str, Claim] = {}
    per_site: Counter[str] = Counter()
    for npc in world.npcs_in_order():
        if not world.config.professions[npc.profession].output:
            continue
        site = str(npc.site)
        per_site[site] += 1
        claim_id = f"{site}-{per_site[site]:02d}"
        claims[claim_id] = Claim(claim_id, site, owner=npc.id, worker=npc.id)
    return claims


def step(world: World, records: dict[str, DailyRecord]) -> ClaimsReport:
    report = ClaimsReport()
    collect_rent(world, records, report)
    trade(world, report)
    report.top10_share = _top10_share(world)
    return report


def collect_rent(world: World, records: dict[str, DailyRecord], report: ClaimsReport) -> None:
    cfg = world.config.claims
    for claim in world.claims.values():
        rec = records.get(claim.worker)
        value = sum(q * world.prices[g] for g, q in rec.produced.items()) if rec else 0.0
        claim.output_value.append(round(value, 4))
        if claim.owner == claim.worker:
            continue
        tenant = world.npcs[claim.worker]
        owed = cfg.rent_share * value + tenant.carry.get(RENT_CARRY, 0.0)
        due = int(owed)
        tenant.carry[RENT_CARRY] = round(owed - due, 9)
        coin = world.ledger.balance(tenant.account, Asset.COIN)
        paid = min(due, max(coin - cfg.rent_floor, 0))
        if paid:
            world.ledger.transfer(
                tenant.account, claim.owner, Asset.COIN, paid, tick=world.tick, reason="rent"
            )
        report.rent_paid += paid
        report.rent_unpaid += due - paid
        report.paid_by[claim.worker] += paid
        report.received_by[claim.owner] += paid


def price(world: World, claim: Claim) -> int:
    """``price_days`` days of the claim's rent at its recent output value."""
    cfg = world.config.claims
    recent = fmean(claim.output_value) if claim.output_value else 0.0
    return int(cfg.price_days * cfg.rent_share * recent)


def trade(world: World, report: ClaimsReport) -> None:
    """Each owner below ``sell_below`` sells one claim (lowest id first) in NPC id order."""
    cfg = world.config.claims
    by_owner: dict[str, list[Claim]] = {}
    for claim in world.claims.values():
        by_owner.setdefault(claim.owner, []).append(claim)
    for seller in sorted(by_owner):
        if world.ledger.balance(seller, Asset.COIN) >= cfg.sell_below:
            continue
        claim = min(by_owner[seller], key=lambda c: c.id)
        cost = price(world, claim)
        buyer = _buyer(world, seller, cost)
        if cost <= 0 or buyer is None:
            continue
        world.ledger.transfer(buyer, seller, Asset.COIN, cost, tick=world.tick, reason="claim sale")
        claim.owner = buyer
        report.sold += 1
        report.sale_value += cost


def holdings(world: World) -> dict[str, tuple[int, int]]:
    """Per NPC id: (claims owned, their value at today's ``price``)."""
    out = {n.id: (0, 0) for n in world.npcs_in_order()}
    for claim in world.claims.values():
        owned, value = out[claim.owner]
        out[claim.owner] = (owned + 1, value + price(world, claim))
    return out


def wealth(world: World) -> list[int]:
    """Each NPC's coin plus the value of the claims they own, in NPC id order."""
    owned = holdings(world)
    return [
        world.ledger.balance(n.account, Asset.COIN) + owned[n.id][1] for n in world.npcs_in_order()
    ]


def _buyer(world: World, seller: str, cost: int) -> str | None:
    """The richest NPC other than ``seller`` who keeps ``buy_reserve`` after paying; ties go to
    the lowest id."""
    best: tuple[int, str] | None = None
    for npc in world.npcs_in_order():
        coin = world.ledger.balance(npc.account, Asset.COIN)
        if npc.id == seller or coin - cost < world.config.claims.buy_reserve:
            continue
        if best is None or coin > best[0]:
            best = (coin, npc.id)
    return best[1] if best else None


def _top10_share(world: World) -> float:
    if not world.claims:
        return 0.0
    ranked = sorted(
        world.npcs_in_order(), key=lambda n: (-world.ledger.balance(n.account, Asset.COIN), n.id)
    )
    top = {n.id for n in ranked[: max(1, ceil(len(ranked) / 10))]}
    return sum(c.owner in top for c in world.claims.values()) / len(world.claims)


def check(world: World) -> None:
    for claim in world.claims.values():
        for role in ("owner", "worker"):
            npc = getattr(claim, role)
            if npc not in world.npcs:
                raise AssertionError(f"claim {claim.id}: {role} {npc} is not an NPC")
    workers = Counter(c.worker for c in world.claims.values())
    if doubled := [w for w, n in workers.items() if n > 1]:
        raise AssertionError(f"NPCs working more than one claim: {doubled}")


def state(world: World) -> list[list]:
    return [
        [c.id, c.owner, c.worker, [round(v, 4) for v in c.output_value]]
        for c in world.claims.values()
    ]
