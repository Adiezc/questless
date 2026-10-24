# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Stylized facts: patterns real economies show, checked against the simulation on several seeds.
Each test names the fact it checks in docs/VALIDATION.md; a known divergence is an ``xfail`` with
``strict=True``, so fixing it fails the test and prompts updating the page."""

import statistics as st

import pytest

from questless.api import Simulation
from questless.sim.ledger import Asset
from tests.conftest import SCENARIOS

SEEDS = range(1, 6)
BEFORE = slice(10, 15)  # after warm-up, before the scenarios' shocks start on day 15


def _world(scenario: str, seed: int, days: int = 120):
    sim = Simulation.from_scenario(SCENARIOS / f"{scenario}.toml", seed=seed)
    sim.step(days)
    return sim.world


def _price(world, good: Asset, days: slice) -> float:
    return st.fmean(s.prices[good] for s in world.stats[days])


def _shock_days(world) -> slice:
    shock = world.modifiers.shocks[0]
    return slice(shock.start, shock.end)


@pytest.mark.parametrize(
    ("scenario", "good"), [("mine_disaster", Asset.IRON_ORE), ("drought", Asset.FOOD)]
)
def test_fact_1_a_supply_shock_raises_the_price(scenario, good):
    for seed in SEEDS:
        w = _world(scenario, seed)
        before, during = _price(w, good, BEFORE), _price(w, good, _shock_days(w))
        assert during > 1.1 * before, (seed, before, during)


def test_fact_2_food_prices_come_back_after_a_drought():
    for seed in SEEDS:
        w = _world("drought", seed)
        before, late = _price(w, Asset.FOOD, BEFORE), _price(w, Asset.FOOD, slice(-20, None))
        assert late < 1.4 * before, (seed, before, late)


@pytest.mark.xfail(
    strict=True,
    reason="divergence D1: after the mine disaster, iron ore settles far below or pinned above "
    "its pre-shock price instead of returning to it",
)
def test_fact_2_ore_prices_come_back_after_a_mine_disaster():
    for seed in SEEDS:
        w = _world("mine_disaster", seed)
        before = _price(w, Asset.IRON_ORE, BEFORE)
        late = _price(w, Asset.IRON_ORE, slice(-20, None))
        assert 0.6 * before < late < 1.4 * before, (seed, before, late)


def test_fact_3_a_food_shortage_leaves_people_hungry():
    for seed in SEEDS:
        w = _world("drought", seed)
        hungry_before = st.fmean(s.hungry_npcs for s in w.stats[BEFORE])
        hungry_during = st.fmean(s.hungry_npcs for s in w.stats[_shock_days(w)])
        assert hungry_during >= hungry_before + 5, (seed, hungry_before, hungry_during)


def _rank_correlation(a: list[int], b: list[int]) -> float:
    def ranks(v: list[int]) -> list[float]:
        order = sorted(range(len(v)), key=v.__getitem__)
        out = [0.0] * len(v)
        for rank, i in enumerate(order):
            out[i] = rank
        return out

    return st.correlation(ranks(a), ranks(b))


def _coins(sim: Simulation) -> list[int]:
    return [sim.world.ledger.balance(n.account, Asset.COIN) for n in sim.world.npcs_in_order()]


@pytest.mark.parametrize("scenario", ["baseline", "iron_shortage"])
def test_fact_4_wealth_ranks_persist_but_are_not_fixed(scenario):
    rhos = []
    for seed in SEEDS:
        sim = Simulation.from_scenario(SCENARIOS / f"{scenario}.toml", seed=seed)
        sim.step(30)
        early = _coins(sim)
        sim.step(90)
        rhos.append(_rank_correlation(early, _coins(sim)))
    assert 0.1 < st.fmean(rhos) < 0.8, rhos


def test_divergence_d2_in_normal_times_coin_is_far_more_equal_than_real_wealth():
    """Real wealth is far more concentrated (global wealth Gini 0.92 in 2014). The baseline stays
    below 0.4; if it ever passes that, docs/VALIDATION.md's divergence D2 is out of date. (A
    severe shock goes higher: the mine disaster peaks near 0.67.)"""
    for seed in SEEDS:
        w = _world("baseline", seed)
        assert max(s.coin_gini for s in w.stats) < 0.4, seed
