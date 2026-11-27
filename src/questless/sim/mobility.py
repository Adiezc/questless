# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Job switching (``[mobility]``, off unless ``enabled``). An NPC in a mobile profession moves to
another when that would clearly pay better, so labour can leave a crowded trade and enter a
scarce one (docs/VALIDATION.md D3).

Each day, before anyone works, every eligible NPC compares what it actually earned over the last
``window`` days with the going rate in each other mobile profession: the median that trade's
members actually earned, scaled to its own skill. A price alone would mislead: in a locked
market tools look very profitable, but most smiths can't afford ore and earn nothing. It switches
when the best alternative beats its realised income by ``margin`` and by at least ``min_gain``
coin a day. At most ``max_per_day``
NPCs switch, the worst-off first, and each then waits ``cooldown`` days, so a single good day for
one trade can't pull everyone into it at once.

A move keeps the NPC's traits, coin and goods. Stock left at the old site comes home to its
market account (without haulage). It joins the new trade's guild; the new guild takes over any
loan the old one made, paying the old guild in coin, and if it can't, the NPC stays put. Nobody
moves while they are a beneficiary of a live contract, since contracts are pooled by guild.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from typing import TYPE_CHECKING

from questless.sim.entities import Profession
from questless.sim.guilds import LOAN
from questless.sim.ledger import Asset

if TYPE_CHECKING:
    from questless.sim.entities import NPC
    from questless.sim.world import World

UNTIL = "mobility_until"  # NPC.carry key: first tick the NPC may switch again


@dataclass(frozen=True, slots=True)
class Move:
    npc_id: str
    old: Profession
    new: Profession
    realised: float  # coin a day over the window, in the old profession
    expected: float  # coin a day expected in the new one


def expected_income(world: World, npc: NPC, profession: Profession) -> float:
    """Coin a day ``npc`` would expect in ``profession`` at today's prices: a gatherer's output
    value net of haulage, or a crafter's best recipe margin, times skill, less equipment wear."""
    pc = world.config.professions[profession]
    skill = npc.traits.skill
    if pc.recipes:
        margin = max(
            world.unit_price(out) - sum(world.unit_price(a) * q for a, q in inputs.items())
            for out, inputs in pc.recipes.items()
        )
        gross = max(margin, 0) * pc.crafts_per_day * skill
    else:
        fee = world.config.transport.fee_rate if pc.site.value != "market" else 0.0
        gross = sum(rate * skill * world.unit_price(g) for g, rate in pc.output.items())
        gross *= 1 - fee
    wear = pc.wear * world.unit_price(pc.equipment) if pc.equipment is not None else 0.0
    return gross - wear


def realised_income(world: World, npc: NPC, window: int) -> float:
    """What ``npc`` earned a day in its current trade over the last ``window`` days, estimated as
    its expected income on the days it actually produced something."""
    recent = list(npc.history)[-window:]
    if not recent:
        return expected_income(world, npc, npc.profession)
    worked = sum(bool(r.produced) for r in recent) / len(recent)
    return worked * expected_income(world, npc, npc.profession)


def _going_rate(world: World, profession: Profession, window: int) -> float | None:
    """Median realised income per unit of skill among ``profession``'s current members, or
    ``None`` if it has none with a full window of history."""
    rates = sorted(
        realised_income(world, n, window) / n.traits.skill
        for n in world.npcs_by_profession(profession)
        if len(n.history) >= window
    )
    if not rates:
        return None
    mid = len(rates) // 2
    return rates[mid] if len(rates) % 2 else (rates[mid - 1] + rates[mid]) / 2


def step(world: World) -> list[Move]:
    """Run today's switches. Called at the start of the tick, before anyone works."""
    cfg = world.config.mobility
    mobile = [p for p in Profession if p.value in cfg.professions]
    live = {b for c in world.contracts.live() for b in c.beneficiaries}
    # What each trade's members actually earn, per unit of skill: the evidence a newcomer would
    # go on. The median, so a few rich survivors don't advertise a trade most members can't live by.
    going_rate = {p: _going_rate(world, p, cfg.window) for p in mobile}
    candidates = []
    for npc in world.npcs_in_order():
        if (
            npc.profession not in mobile
            or npc.id in live
            or world.tick < npc.carry.get(UNTIL, 0)
            or len(npc.history) < cfg.window
            or any(r.produced for r in list(npc.history)[-cfg.idle_days :])  # still working
        ):
            continue
        realised = realised_income(world, npc, cfg.window)
        options = [
            (rate * npc.traits.skill, -i, p)
            for i, p in enumerate(mobile)
            if (rate := going_rate[p]) is not None
        ]
        if not any(o[2] is not npc.profession for o in options):
            continue
        best, _, target = max(o for o in options if o[2] is not npc.profession)
        if best >= cfg.margin * max(realised, 0) and best - realised >= cfg.min_gain:
            candidates.append((realised / best if best else 1.0, npc.id, target, realised, best))
    moves: list[Move] = []
    for _, npc_id, target, realised, best in sorted(candidates):
        if len(moves) >= cfg.max_per_day:
            break
        npc = world.npcs[npc_id]
        old = npc.profession
        if _switch(world, npc, target):
            npc.carry[UNTIL] = float(world.tick + cfg.cooldown)
            moves.append(Move(npc_id, old, target, round(realised, 2), round(best, 2)))
    return moves


def _switch(world: World, npc: NPC, target: Profession) -> bool:
    ledger = world.ledger
    old_guild = world.guilds.get(npc.guild_id) if npc.guild_id else None
    new_gid = next(
        (gid for gid, gc in sorted(world.config.guilds.items()) if target in gc.professions),
        None,
    )
    new_guild = world.guilds.get(new_gid) if new_gid else None
    debt = int(npc.carry.get(LOAN, 0))
    if debt and old_guild is not new_guild:
        # The new guild buys the loan from the old one; with no guild to take it on, or one that
        # can't afford it while keeping half its reserve, the NPC stays where it is.
        if new_guild is None or old_guild is None:
            return False
        spare = ledger.balance(new_guild.account, Asset.COIN) - new_guild.policy.reserve // 2
        if spare < debt:
            return False
        ledger.transfer(
            new_guild.account,
            old_guild.account,
            Asset.COIN,
            debt,
            tick=world.tick,
            reason=f"loan taken over {npc.id}",
        )
    old_site = npc.site_account
    if old_site != npc.account:
        for good, qty in ledger.holdings(old_site).items():
            ledger.transfer(old_site, npc.account, good, qty, tick=world.tick, reason="move")
    npc.profession = target
    npc.site = world.config.professions[target].site
    if not ledger.has_account(npc.site_account):
        ledger.add_empty_account(npc.site_account)
    if old_guild is not new_guild:
        if old_guild is not None:
            old_guild.members.remove(npc.id)
        if new_guild is not None:
            bisect.insort(new_guild.members, npc.id)
        npc.guild_id = new_gid if new_guild is not None else None
    npc.unmet_streak.clear()
    return True
