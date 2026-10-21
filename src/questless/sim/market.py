# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Posted-price market, cleared once per tick per good, then prices adjust to excess demand.

1. Asks: every NPC offers what it holds above its stock target.
2. Bids: every NPC asks for what it lacks below its target, capped by its budget for that good
   (see ``budget``). Crafters only buy inputs while crafting with them is profitable.
3. The short side is filled in full. Excess supply is split across sellers pro rata; excess
   demand is *rationed* equally across buyers (see ``alloc.ration``).
4. Trades settle at today's integer unit price via a clearing account; sellers pay market tax
   to the town.
5. Prices adjust to two signals: a *flow* term (today's consumption vs today's production) and a
   damping *stock* term (days of cover offered vs ``target_cover_days``):
   ``signal = clamp((C - P) / max(C, P) + w * (T - S/D) / T, -1, 1)``,
   ``p' = clamp(p * (1 + alpha * signal))``. Gatherers' effort rises and falls with price (see
   ``behaviour.effort``), so the flow term has a real equilibrium where output meets demand;
   the stock term stops inventories from drifting while the flow is balanced.

Unfilled demand (wanted, could pay, no supply) is the scarcity signal for contracts. Demand that
failed only for lack of money is recorded separately as ``unaffordable``: poverty is not scarcity.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from questless.sim.alloc import allocate, ration
from questless.sim.entities import MARKET, NPC, TOWN
from questless.sim.ledger import GOODS, Asset

if TYPE_CHECKING:
    from questless.sim.world import World


@dataclass(frozen=True, slots=True)
class MarketReport:
    good: Asset
    price: int  # unit price trades settled at
    supply: int  # units offered
    demand: int  # units wanted and affordable
    traded: int
    unfilled: int  # affordable demand left unmet: scarcity
    unaffordable: int  # wanted but not affordable: poverty
    tax: int


def stock_target(world: World, npc: NPC, good: Asset) -> int:
    """How many units of ``good`` this NPC wants on hand: food and inputs for ``stock_days``,
    plus one spare of its equipment."""
    pc = world.config.professions[npc.profession]
    days = npc.traits.stock_days
    target = 0
    if good is Asset.FOOD:
        target += world.config.needs.food_per_day * days
    if good == pc.equipment:
        target += 1
    if pc.crafts_per_day:
        per_craft = max((inputs.get(good, 0) for inputs in pc.recipes.values()), default=0)
        target += per_craft * pc.crafts_per_day * days
    return target


def budget(world: World, npc: NPC, good: Asset) -> int:
    """Coin the NPC will spend on ``good`` today. Food may take the whole wallet; anything else
    must leave a reserve of the larger of ``thrift`` x wallet and the cost of its food target,
    so buying inputs or tools never starves the buyer."""
    wallet = world.ledger.balance(npc.account, Asset.COIN)
    if good is Asset.FOOD:
        return wallet
    food_reserve = stock_target(world, npc, Asset.FOOD) * world.unit_price(Asset.FOOD)
    return max(wallet - max(int(wallet * npc.traits.thrift), food_reserve), 0)


def _worth_buying(world: World, npc: NPC, good: Asset) -> bool:
    """Consumables (food, own equipment) are always worth buying. Crafting inputs only while some
    recipe that uses them sells for more than its inputs cost."""
    pc = world.config.professions[npc.profession]
    if good is Asset.FOOD or good == pc.equipment:
        return True
    return any(
        world.unit_price(out) > sum(world.unit_price(a) * q for a, q in inputs.items())
        for out, inputs in pc.recipes.items()
        if good in inputs
    )


def clear(
    world: World, produced: Mapping[Asset, int], consumed: Mapping[Asset, int]
) -> dict[Asset, MarketReport]:
    """Clear every market, then move prices using today's production and consumption flows."""
    reports = {good: _clear_good(world, good) for good in GOODS}
    _update_prices(world, reports, produced, consumed)
    return reports


def _clear_good(world: World, good: Asset) -> MarketReport:
    price = world.unit_price(good)
    ledger = world.ledger
    asks: list[tuple[str, int]] = []
    bids: list[tuple[str, int]] = []
    unaffordable = 0
    for npc in world.npcs_in_order():
        held = ledger.balance(npc.account, good)
        target = stock_target(world, npc, good)
        if held > target:
            asks.append((npc.id, held - target))
        elif held < target and _worth_buying(world, npc, good):
            want = target - held
            bid = min(want, budget(world, npc, good) // price)
            unaffordable += want - bid
            if want > bid:
                _add(_rec(npc).unaffordable, good, want - bid)
            if bid:
                bids.append((npc.id, bid))

    supply = sum(q for _, q in asks)
    demand = sum(q for _, q in bids)
    rng = world.rng.stream("market")
    sold = allocate(demand, asks, rng)
    bought = ration(supply, bids, rng)  # equal shares in a shortage, not wealth-weighted
    traded = sum(sold.values())
    assert traded == sum(bought.values())

    tax_total = 0
    for seller, qty in sorted(sold.items()):
        if qty:
            ledger.transfer(seller, MARKET, good, qty, tick=world.tick, reason="market sale")
    for buyer, qty in sorted(bought.items()):
        if qty:
            ledger.transfer(MARKET, buyer, good, qty, tick=world.tick, reason="market purchase")
            ledger.transfer(buyer, MARKET, Asset.COIN, qty * price, tick=world.tick, reason="pay")
            _add(_rec(world.npcs[buyer]).bought, good, qty)
    for seller, qty in sorted(sold.items()):
        if qty:
            value = qty * price
            tax = int(value * world.config.town.market_tax)
            ledger.transfer(MARKET, seller, Asset.COIN, value, tick=world.tick, reason="proceeds")
            ledger.transfer(seller, TOWN, Asset.COIN, tax, tick=world.tick, reason="market tax")
            tax_total += tax
            _add(_rec(world.npcs[seller]).sold, good, qty)
    for buyer, bid in bids:
        short = bid - bought.get(buyer, 0)
        if short:
            _add(_rec(world.npcs[buyer]).unfilled, good, short)

    return MarketReport(
        good=good,
        price=price,
        supply=supply,
        demand=demand,
        traded=traded,
        unfilled=demand - traded,
        unaffordable=unaffordable,
        tax=tax_total,
    )


def price_signal(
    supply: int,
    demand: int,
    produced: int,
    consumed: int,
    target_cover: float,
    stock_weight: float,
) -> float:
    """-1 (glut) .. +1 (scarcity). Zero when production matches consumption and the stock on
    offer covers ``target_cover`` days of demand."""
    flow = (consumed - produced) / max(consumed, produced, 1)
    if demand:
        stock = max(-1.0, (target_cover - supply / demand) / target_cover)
    else:
        stock = -1.0 if supply else 0.0
    return max(-1.0, min(1.0, flow + stock_weight * stock))


def _update_prices(
    world: World,
    reports: dict[Asset, MarketReport],
    produced: Mapping[Asset, int],
    consumed: Mapping[Asset, int],
) -> None:
    mc = world.config.market
    alpha = mc.price_adjustment
    for good, r in reports.items():
        signal = price_signal(
            r.supply,
            r.demand,
            produced.get(good, 0),
            consumed.get(good, 0),
            mc.target_cover_days,
            mc.stock_weight,
        )
        if not signal:
            continue
        gc = world.config.goods[good]
        new = world.prices[good] * (1 + alpha * signal)
        world.prices[good] = round(
            min(max(new, gc.base_price * gc.price_floor), gc.base_price * gc.price_ceiling), 9
        )


def _rec(npc: NPC):
    """Today's record for the NPC (appended earlier in the tick by its daily rules)."""
    return npc.history[-1]


def _add(counter: dict[Asset, int], good: Asset, qty: int) -> None:
    counter[good] = counter.get(good, 0) + qty
