# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M4 acceptance: dues move coin member -> guild; relief tops up broke members within budget and
reserve; with guilds disabled no guild account is ever touched."""

import dataclasses
import statistics

import pytest

from questless.api import Simulation
from questless.sim.entities import OUTSIDE
from questless.sim.guilds import collect_dues, provide_relief, working_capital
from questless.sim.ledger import Asset
from questless.sim.world import TickStats, build_world
from tests.conftest import SCENARIOS


@pytest.fixture
def world(baseline):
    return build_world(baseline)


def _coin(world, account):
    return world.ledger.balance(account, Asset.COIN)


def _set_coin(world, account, amount):
    current = _coin(world, account)
    if current > amount:
        world.ledger.transfer(account, OUTSIDE, Asset.COIN, current - amount, tick=0, reason="test")
    elif current < amount:
        world.ledger.transfer(OUTSIDE, account, Asset.COIN, amount - current, tick=0, reason="test")


def _fund_outside(world, amount=100_000):
    world.ledger._balances[OUTSIDE][Asset.COIN] += amount  # test-only top-up
    world.ledger._genesis[Asset.COIN] += amount


def test_dues_are_a_share_of_net_gain(world):
    guild = world.guilds["blacksmiths"]
    member = guild.members[0]
    start = {n: _coin(world, n) for n in world.npcs}
    _fund_outside(world)
    world.ledger.transfer(OUTSIDE, member, Asset.COIN, 100, tick=0, reason="test income")
    treasury = _coin(world, guild.account)
    collected = collect_dues(world, start, relief={})
    assert collected["blacksmiths"] == int(100 * guild.dues_rate)
    assert _coin(world, guild.account) - treasury == collected["blacksmiths"]
    world.check_invariants()


def test_small_incomes_still_pay_dues_over_time(world):
    guild = world.guilds["miners"]
    member = guild.members[0]
    _fund_outside(world)
    total = 0
    for _ in range(20):
        start = {n: _coin(world, n) for n in world.npcs}
        world.ledger.transfer(OUTSIDE, member, Asset.COIN, 4, tick=0, reason="test income")
        total += collect_dues(world, start, relief={})["miners"]
    assert total == int(20 * 4 * guild.dues_rate)  # 0.2/day would round to 0 without carry


def test_relief_is_not_charged_dues(world):
    guild = world.guilds["miners"]
    member = guild.members[0]
    start = {n: _coin(world, n) for n in world.npcs}
    _set_coin(world, member, 0)
    start[member] = 0
    relief = provide_relief(world)
    assert relief["miners"][member] > 0
    assert collect_dues(world, start, relief)["miners"] == 0


def test_relief_tops_broke_members_up_to_working_capital_poorest_first(world):
    guild = world.guilds["blacksmiths"]
    poorest, poor = guild.members[0], guild.members[1]
    floor = working_capital(world, poorest, guild.policy.relief_days)
    assert floor == working_capital(world, poor, guild.policy.relief_days)
    # food for relief_days plus the cheapest craft's inputs (both smiths still have tools)
    cheapest_craft = 2 * world.unit_price(Asset.IRON_ORE)
    assert floor == guild.policy.relief_days * world.unit_price(Asset.FOOD) + cheapest_craft
    _set_coin(world, poorest, 0)
    _set_coin(world, poor, floor - 2)
    paid = provide_relief(world)["blacksmiths"]
    assert paid[poorest] == floor and paid[poor] == 2
    assert _coin(world, poorest) == _coin(world, poor) == floor
    assert list(paid)[0] == poorest


def test_relief_respects_daily_budget_and_reserve(world):
    guild = world.guilds["blacksmiths"]
    for member in guild.members:
        _set_coin(world, member, 0)
    _set_coin(world, guild.account, guild.policy.reserve + 3)
    paid = provide_relief(world)["blacksmiths"]
    assert sum(paid.values()) <= 3
    assert _coin(world, guild.account) >= guild.policy.reserve


def test_guilds_disabled_never_touch_guild_accounts(baseline):
    world = build_world(dataclasses.replace(baseline, guilds_enabled=False))
    world.step(60)
    touched = [
        e
        for e in world.ledger.journal
        if (e.src or "").startswith("guild:") or (e.dst or "").startswith("guild:")
    ]
    assert touched == []
    assert all(s.guilds == {} for s in world.stats)


def test_guild_relief_reduces_hunger_on_average(baseline):
    """A statistical claim, so it is tested over several seeds (one seed can go either way)."""

    def mean_hungry(enabled: bool) -> float:
        runs = []
        for seed in (1, 2, 3, 4):
            cfg = dataclasses.replace(baseline, guilds_enabled=enabled, seed=seed)
            world = build_world(cfg)
            world.step(365)
            runs.append(statistics.mean(s.hungry_npcs for s in world.stats[100:]))
        return statistics.mean(runs)

    assert mean_hungry(True) < mean_hungry(False)


def test_year_with_guilds_conserves_everything(world):
    world.step(365)  # invariants are checked every tick
    for report in world.stats[-1].guilds.values():
        assert report.treasury >= 0


def test_treasury_card_matches_chart_after_escrow():
    """M13.3: the report is re-read after the contract board moves escrow, so the dashboard's
    treasury card (a live balance) equals the chart's last point every day."""
    sim = Simulation.from_scenario(SCENARIOS / "mine_disaster.toml")
    saw_escrow = False
    for _ in range(90):
        sim.step(1)
        series = sim.timeseries()
        for gid, guild in sim.world.guilds.items():
            assert sim.guild(gid)["treasury"] == series["treasury"][gid][-1]
            locked = sum(c.reward for c in sim.world.contracts.live() if c.funder == guild.account)
            assert series["escrowed"][gid][-1] == locked
            saw_escrow |= locked > 0
    assert saw_escrow, "no guild funded a contract, so the test proved nothing"


def _cap_guilds(cfg, cap):
    guilds = {
        gid: dataclasses.replace(g, policy=dataclasses.replace(g.policy, max_treasury=cap))
        for gid, g in cfg.guilds.items()
    }
    return dataclasses.replace(cfg, guilds=guilds)


def test_guild_above_max_treasury_pays_upkeep_on_the_excess(baseline):
    """#48: coin above ``max_treasury`` pays the town levy; at or below it, nothing."""
    world = build_world(_cap_guilds(baseline, 1000))
    _fund_outside(world)
    rich, *others = sorted(world.guilds)
    _set_coin(world, world.guilds[rich].account, 3000)
    for gid in others:
        _set_coin(world, world.guilds[gid].account, 1000)
    town = _coin(world, "town")
    stats = TickStats(0)
    paid = world._collect_upkeep(stats)
    expected = int(2000 * baseline.town.upkeep_rate)
    assert paid == {rich: expected, **{gid: 0 for gid in others}}
    assert _coin(world, world.guilds[rich].account) == 3000 - expected
    assert _coin(world, "town") == town + stats.upkeep  # NPC and guild levy both reach the town
    world.ledger.check_conservation()


def test_guilds_without_max_treasury_are_exempt(baseline):
    world = build_world(_cap_guilds(baseline, None))
    _fund_outside(world)
    for gid in world.guilds:
        _set_coin(world, world.guilds[gid].account, 20_000)
    assert world._collect_upkeep(TickStats(0)) == {}
    assert all(_coin(world, g.account) == 20_000 for g in world.guilds.values())


def test_guild_upkeep_is_reported(baseline):
    world = build_world(_cap_guilds(baseline, 0))
    world.step(3)
    reports = world.stats[-1].guilds.values()
    assert any(r.upkeep > 0 for r in reports)
    world.check_invariants()
