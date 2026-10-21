# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
import dataclasses

import pytest

from questless.sim.behaviour import eat, maintain, run_npc_day
from questless.sim.entities import OUTSIDE, TOWN, DailyRecord, NPCState, Profession
from questless.sim.ledger import Asset
from questless.sim.world import build_world


@pytest.fixture
def world(baseline):
    return build_world(baseline)


def _first(world, profession):
    return world.npcs_by_profession(profession)[0]


def _remove_all(world, account, asset):
    world.ledger.transfer(
        account, OUTSIDE, asset, world.ledger.balance(account, asset), tick=0, reason="test"
    )


def test_eating_consumes_food_and_resets_hunger(world):
    npc = _first(world, Profession.GUARD)
    npc.hunger = 3
    rec = DailyRecord(tick=0)
    eat(world, npc, rec)
    assert npc.hunger == 0
    assert rec.consumed[Asset.FOOD] == 1
    assert world.ledger.balance(npc.account, Asset.FOOD) == 4


def test_no_food_increases_hunger_and_records_unmet_need(world):
    npc = _first(world, Profession.GUARD)
    _remove_all(world, npc.account, Asset.FOOD)
    rec = DailyRecord(tick=0)
    eat(world, npc, rec)
    assert npc.hunger == 1
    assert rec.unmet == {Asset.FOOD: 1}


def test_farmer_eats_own_harvest_waiting_at_the_farm(world):
    npc = _first(world, Profession.FARMER)
    _remove_all(world, npc.account, Asset.FOOD)
    world.ledger.transfer(OUTSIDE, npc.site_account, Asset.FOOD, 2, tick=0, reason="test")
    eat(world, npc, DailyRecord(tick=0))
    assert npc.hunger == 0
    assert world.ledger.balance(npc.site_account, Asset.FOOD) == 1


def test_broken_equipment_is_replaced_from_stock(world):
    npc = _first(world, Profession.MINER)
    npc.tool_condition = 0.1
    rec = DailyRecord(tick=0)
    maintain(world, npc, rec)
    assert npc.tool_condition == 1.0
    assert world.ledger.balance(npc.account, Asset.TOOLS) == 0
    assert rec.consumed == {Asset.TOOLS: 1}


def test_broken_equipment_without_spare_is_an_unmet_need_and_slows_work(world):
    npc = _first(world, Profession.MINER)
    _remove_all(world, npc.account, Asset.TOOLS)
    npc.tool_condition = 0.1
    npc.carry.clear()
    rec = run_npc_day(world, npc)
    assert rec.unmet[Asset.TOOLS] == 1
    pc = world.config.professions[Profession.MINER]
    expected = pc.output[Asset.IRON_ORE] * npc.traits.skill * pc.no_tool_factor  # effort is 1.0
    assert rec.produced.get(Asset.IRON_ORE, 0) + npc.carry["iron_ore"] == pytest.approx(expected)


def test_gatherer_output_lands_at_the_site_not_the_market(world):
    npc = _first(world, Profession.MINER)
    run_npc_day(world, npc)
    assert world.ledger.balance(npc.site_account, Asset.IRON_ORE) > 0
    assert world.ledger.balance(npc.account, Asset.IRON_ORE) == 0


def test_smith_crafts_the_higher_margin_recipe(world):
    smith = _first(world, Profession.BLACKSMITH)
    world.prices[Asset.WEAPONS] = 200  # weapons now far more profitable per unit of ore
    rec = run_npc_day(world, smith)
    assert rec.produced.get(Asset.WEAPONS, 0) >= 1
    assert Asset.TOOLS not in rec.produced


def test_smith_without_ore_is_idle_and_needs_ore(world):
    smith = _first(world, Profession.BLACKSMITH)
    _remove_all(world, smith.account, Asset.IRON_ORE)
    rec = run_npc_day(world, smith)
    assert rec.idle
    assert smith.state is NPCState.IDLE_NO_INPUT
    assert rec.unmet[Asset.IRON_ORE] > 0
    assert smith.unmet_streak[Asset.IRON_ORE] == 1


def test_crafting_never_uses_inputs_the_smith_does_not_have(world):
    smith = _first(world, Profession.BLACKSMITH)
    _remove_all(world, smith.account, Asset.IRON_ORE)
    world.ledger.transfer(OUTSIDE, smith.account, Asset.IRON_ORE, 3, tick=0, reason="test")
    world.prices[Asset.WEAPONS] = 1.0  # make tools (2 ore) the preferred recipe
    rec = run_npc_day(world, smith)
    assert rec.produced == {Asset.TOOLS: 1}  # 3 ore: one tools craft (2 ore), 1 left over
    assert world.ledger.balance(smith.account, Asset.IRON_ORE) == 1


def test_town_pays_guards_until_its_treasury_runs_out(baseline):
    no_upkeep = dataclasses.replace(baseline.town, upkeep_rate=0.0)
    world = build_world(dataclasses.replace(baseline, town=no_upkeep))
    wage = baseline.town.guard_wage
    guards = baseline.professions[Profession.GUARD].count
    world.ledger.transfer(
        TOWN,
        OUTSIDE,
        Asset.COIN,
        world.ledger.balance(TOWN, Asset.COIN) - 30,
        tick=0,
        reason="test",
    )
    world.step()
    stats = world.stats[-1]
    paid_guards = 30 // wage
    assert stats.wages_paid == paid_guards * wage
    assert stats.wages_unpaid == (guards - paid_guards) * wage
    assert world.ledger.balance(TOWN, Asset.COIN) >= 0  # never overdrawn
