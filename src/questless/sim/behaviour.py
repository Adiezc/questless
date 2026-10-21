# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""NPC daily rules, in priority order: eat, maintain equipment, produce.

Trading (milestone M3) and need escalation (M5) run later in the tick. Every effect on goods goes
through the ledger; this module only decides *what* happens.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from questless.sim.entities import NPC, DailyRecord, NPCState
from questless.sim.ledger import Asset
from questless.sim.market import stock_target

if TYPE_CHECKING:
    from questless.sim.world import World

CRAFT_CARRY = "craft"


def run_npc_day(world: World, npc: NPC) -> DailyRecord:
    rec = DailyRecord(tick=world.tick)
    eat(world, npc, rec)
    maintain(world, npc, rec)
    produce(world, npc, rec)
    wear(world, npc)
    _update_state(world, npc, rec)
    return rec


def eat(world: World, npc: NPC, rec: DailyRecord) -> None:
    need = world.config.needs.food_per_day
    eaten = 0
    # Personal stock first, then own output still waiting at the site (a farmer eats their harvest).
    for account in dict.fromkeys((npc.account, npc.site_account)):
        take = min(need - eaten, world.ledger.balance(account, Asset.FOOD))
        world.ledger.consume(account, Asset.FOOD, take, tick=world.tick, reason="eat")
        eaten += take
    _add(rec.consumed, Asset.FOOD, eaten)
    if eaten < need:
        npc.hunger += 1
        _add(rec.unmet, Asset.FOOD, need - eaten)
    else:
        npc.hunger = 0


def maintain(world: World, npc: NPC, rec: DailyRecord) -> None:
    pc = world.config.professions[npc.profession]
    if pc.equipment is None or npc.tool_condition >= world.config.needs.equipment_threshold:
        return
    if world.ledger.balance(npc.account, pc.equipment) >= 1:
        world.ledger.consume(
            npc.account, pc.equipment, 1, tick=world.tick, reason="equipment replaced"
        )
        _add(rec.consumed, pc.equipment, 1)
        npc.tool_condition = 1.0
    else:
        _add(rec.unmet, pc.equipment, 1)


def productivity(world: World, npc: NPC) -> float:
    pc = world.config.professions[npc.profession]
    needs = world.config.needs
    factor = npc.traits.skill * world.modifiers.site_output(npc.site, world.tick)
    if npc.hunger > needs.hungry_after:
        factor *= needs.hungry_productivity
    if pc.equipment is not None and npc.tool_condition < needs.equipment_threshold:
        factor *= pc.no_tool_factor
    return factor


def produce(world: World, npc: NPC, rec: DailyRecord) -> None:
    """Gather or craft, but never hold more than ``max_unsold_days`` of recent *sales* unsold:
    an NPC who cannot sell slows down instead of producing into the void."""
    pc = world.config.professions[npc.profession]
    factor = productivity(world, npc)

    for good, base in pc.output.items():
        if unsold(world, npc, good) >= unsold_cap(world, npc, good, base):
            rec.slack = True
            continue
        qty = _whole_units(npc, str(good), base * factor * effort(world, good))
        world.ledger.produce(npc.site_account, good, qty, tick=world.tick, reason="gather")
        _add(rec.produced, good, qty)

    if pc.crafts_per_day:
        caps = {
            g: unsold_cap(world, npc, g, pc.crafts_per_day / len(pc.recipes)) for g in pc.recipes
        }
        if all(unsold(world, npc, g) >= caps[g] for g in pc.recipes):
            rec.slack = True
            return
        _craft(world, npc, rec, _whole_units(npc, CRAFT_CARRY, pc.crafts_per_day * factor), caps)


SALES_WINDOW = 7


def unsold_cap(world: World, npc: NPC, good: Asset, base_rate: float) -> float:
    """``max_unsold_days`` worth of recent daily sales, with a floor of half the base production
    rate so a producer with no sales history can still put goods on the market."""
    recent = list(npc.history)[-SALES_WINDOW:]
    avg_sales = sum(r.sold.get(good, 0) for r in recent) / SALES_WINDOW
    return world.config.needs.max_unsold_days * max(avg_sales, 0.5 * base_rate)


def effort(world: World, good: Asset) -> float:
    """Gatherers work harder when their goods fetch more than the base price, and ease off when
    they fetch less. This gives the market an upward-sloping supply curve."""
    lo, hi = world.config.market.effort
    return min(max(world.prices[good] / world.config.goods[good].base_price, lo), hi)


def unsold(world: World, npc: NPC, good: Asset) -> int:
    """Units of ``good`` the NPC holds (at market and at its site) beyond its own stock target."""
    held = world.ledger.balance(npc.account, good)
    if npc.site_account != npc.account:
        held += world.ledger.balance(npc.site_account, good)
    return held - stock_target(world, npc, good)


def _craft(world: World, npc: NPC, rec: DailyRecord, crafts: int, caps: dict[Asset, float]) -> None:
    """Craft up to ``crafts`` units, each time picking, among recipes whose output is still below
    its unsold cap, the best margin per input unit at current prices that the NPC can make from
    stock. Ties go to config order."""
    recipes = world.config.professions[npc.profession].recipes
    ranked = sorted(recipes.items(), key=lambda item: -_margin_per_input(world, *item))
    for done in range(crafts):
        wanted = [(g, inputs) for g, inputs in ranked if unsold(world, npc, g) < caps[g]]
        if not wanted:
            return
        for good, inputs in wanted:
            if all(world.ledger.balance(npc.account, a) >= q for a, q in inputs.items()):
                for a, q in inputs.items():
                    world.ledger.consume(npc.account, a, q, tick=world.tick, reason=f"craft {good}")
                    _add(rec.consumed, a, q)
                world.ledger.produce(npc.account, good, 1, tick=world.tick, reason="craft")
                _add(rec.produced, good, 1)
                break
        else:
            # Out of inputs: record what the remaining crafts of the preferred recipe would need.
            _, preferred = wanted[0]
            for a, q in preferred.items():
                short = q * (crafts - done) - world.ledger.balance(npc.account, a)
                _add(rec.unmet, a, max(short, 0))
            rec.idle = done == 0
            return


def _margin_per_input(world: World, good: Asset, inputs: dict[Asset, int]) -> float:
    cost = sum(world.prices[a] * q for a, q in inputs.items())
    return (world.prices[good] - cost) / max(sum(inputs.values()), 1)


def wear(world: World, npc: NPC) -> None:
    """Equipment wears by time worked, not by output, so shocks don't change wear rates."""
    pc = world.config.professions[npc.profession]
    if pc.equipment is not None and pc.wear:
        npc.tool_condition = max(0.0, round(npc.tool_condition - pc.wear, 9))


def _update_state(world: World, npc: NPC, rec: DailyRecord) -> None:
    for good in sorted(set(npc.unmet_streak) | set(rec.unmet)):
        if rec.unmet.get(good, 0) > 0:
            npc.unmet_streak[good] = npc.unmet_streak.get(good, 0) + 1
        else:
            npc.unmet_streak.pop(good, None)
    if npc.hunger > world.config.needs.hungry_after:
        npc.state = NPCState.HUNGRY
    elif rec.idle:
        npc.state = NPCState.IDLE_NO_INPUT
    elif rec.slack and not rec.produced:
        npc.state = NPCState.IDLE_NO_DEMAND
    else:
        npc.state = NPCState.WORKING
    npc.history.append(rec)


def _whole_units(npc: NPC, key: str, amount: float) -> int:
    total = amount + npc.carry.get(key, 0.0)
    whole = int(total)
    npc.carry[key] = round(total - whole, 9)  # rounding keeps carry stable across platforms
    return whole


def _add(counter: dict[Asset, int], good: Asset, qty: int) -> None:
    if qty:
        counter[good] = counter.get(good, 0) + qty
