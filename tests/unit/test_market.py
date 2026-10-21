# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M3 acceptance: excess demand raises prices, excess supply lowers them, clamps hold, and trading
conserves coin and goods."""

import pytest

from questless.sim.behaviour import effort
from questless.sim.entities import MARKET, OUTSIDE, Profession
from questless.sim.ledger import GOODS, Asset
from questless.sim.market import budget, clear, price_signal, stock_target
from questless.sim.world import build_world


@pytest.fixture
def world(baseline):
    w = build_world(baseline)
    w.step()  # each NPC needs a daily record before the market runs
    return w


def _drain(world, good):
    """Move every unit of ``good`` held by NPCs out of the map."""
    for npc in world.npcs_in_order():
        for account in {npc.account, npc.site_account}:
            qty = world.ledger.balance(account, good)
            world.ledger.transfer(account, OUTSIDE, good, qty, tick=world.tick, reason="test")


def test_price_signal_directions():
    assert price_signal(0, 50, produced=0, consumed=50, target_cover=3, stock_weight=0.5) > 0
    assert price_signal(500, 10, produced=80, consumed=10, target_cover=3, stock_weight=0.5) < 0
    assert price_signal(30, 10, produced=10, consumed=10, target_cover=3, stock_weight=0.5) == 0


def test_excess_demand_raises_price_and_is_recorded_as_unfilled(world):
    _drain(world, Asset.FOOD)
    before = world.prices[Asset.FOOD]
    reports = clear(world, produced={}, consumed={Asset.FOOD: 100})
    assert reports[Asset.FOOD].supply == 0
    assert reports[Asset.FOOD].unfilled == reports[Asset.FOOD].demand > 0
    assert world.prices[Asset.FOOD] > before


def test_excess_supply_lowers_price(world):
    for npc in world.npcs_by_profession(Profession.FARMER):
        world.ledger.transfer(OUTSIDE, npc.account, Asset.FOOD, 50, tick=world.tick, reason="test")
    before = world.prices[Asset.FOOD]
    clear(world, produced={Asset.FOOD: 200}, consumed={Asset.FOOD: 100})
    assert world.prices[Asset.FOOD] < before


def test_prices_stay_within_floor_and_ceiling(world):
    _drain(world, Asset.FOOD)
    gc = world.config.goods[Asset.FOOD]
    for _ in range(200):
        clear(world, produced={}, consumed={Asset.FOOD: 100})
    assert world.prices[Asset.FOOD] == pytest.approx(gc.base_price * gc.price_ceiling)
    for npc in world.npcs_by_profession(Profession.FARMER):
        world.ledger.transfer(OUTSIDE, npc.account, Asset.FOOD, 500, tick=world.tick, reason="test")
    for _ in range(400):
        clear(world, produced={Asset.FOOD: 1000}, consumed={})
    assert world.prices[Asset.FOOD] == pytest.approx(gc.base_price * gc.price_floor)


def test_trading_conserves_coin_and_goods_and_empties_clearing_account(world):
    totals = world.ledger.totals()
    clear(world, produced={}, consumed={})
    assert world.ledger.totals() == totals
    assert world.ledger.holdings(MARKET) == {}
    world.check_invariants()


def test_nobody_spends_their_food_money_on_other_goods(world):
    for npc in world.npcs_in_order():
        reserve = stock_target(world, npc, Asset.FOOD) * world.unit_price(Asset.FOOD)
        wallet = world.ledger.balance(npc.account, Asset.COIN)
        for good in GOODS:
            if good is not Asset.FOOD:
                assert budget(world, npc, good) <= max(wallet - reserve, 0)


def test_broke_npcs_are_unaffordable_not_unfilled(world):
    guard = world.npcs_by_profession(Profession.GUARD)[0]
    coin = world.ledger.balance(guard.account, Asset.COIN)
    world.ledger.transfer(guard.account, OUTSIDE, Asset.COIN, coin, tick=world.tick, reason="test")
    _drain(world, Asset.FOOD)
    clear(world, produced={}, consumed={})
    rec = guard.history[-1]
    assert rec.unaffordable.get(Asset.FOOD, 0) > 0
    assert rec.unfilled.get(Asset.FOOD, 0) == 0


def test_smiths_stop_buying_ore_when_crafting_is_unprofitable(world):
    world.prices[Asset.IRON_ORE] = 40.0  # 2 ore now cost more than tools sell for
    world.prices[Asset.TOOLS] = 24.0
    world.prices[Asset.WEAPONS] = 40.0
    smiths = world.npcs_by_profession(Profession.BLACKSMITH)
    ore_before = [world.ledger.balance(s.account, Asset.IRON_ORE) for s in smiths]
    clear(world, produced={}, consumed={})
    assert [world.ledger.balance(s.account, Asset.IRON_ORE) for s in smiths] == ore_before


def test_effort_follows_price_within_configured_range(world):
    lo, hi = world.config.market.effort
    base = world.config.goods[Asset.FOOD].base_price
    world.prices[Asset.FOOD] = base * 10
    assert effort(world, Asset.FOOD) == hi
    world.prices[Asset.FOOD] = base * 0.01
    assert effort(world, Asset.FOOD) == lo
    world.prices[Asset.FOOD] = base * 1.0
    assert effort(world, Asset.FOOD) == pytest.approx(1.0)
