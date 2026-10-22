# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M14.1 and M14.4: index series ("% of normal") and unmet demand as a share of demand, so goods
with different volumes share one axis."""

import pytest

from questless.api import Simulation
from questless.metrics import REFERENCE_DAYS, _index, _unfilled_pct
from questless.sim.ledger import Asset
from questless.sim.market import MarketReport
from tests.conftest import SCENARIOS


def test_unfilled_pct_is_unfilled_over_demand():
    sim = Simulation.from_scenario(SCENARIOS / "mine_disaster.toml")
    sim.step(120)
    series = sim.timeseries()
    peak = 0.0
    for good, values in series["unfilled_pct"].items():
        assert len(values) == len(series["day"])
        for stats, pct in zip(sim.world.stats, values, strict=True):
            market = stats.market[Asset(good)]
            expected = 100 * market.unfilled / market.demand if market.demand else 0.0
            assert pct == round(expected, 1)
            assert 0.0 <= pct <= 100.0
            peak = max(peak, pct)
    assert peak > 0, "the shock left no demand unmet, so the test proved nothing"


def test_unfilled_pct_is_zero_when_nobody_bids():
    quiet = MarketReport(
        good=Asset.IRON_ORE,
        price=1,
        supply=5,
        demand=0,
        traded=0,
        unfilled=0,
        unaffordable=0,
        tax=0,
    )
    assert _unfilled_pct(quiet) == 0.0


@pytest.mark.parametrize("key", ["price_index", "produced_index"])
def test_index_averages_100_over_the_reference_window(key):
    sim = Simulation.from_scenario(SCENARIOS / "mine_disaster.toml")
    sim.step(60)
    for good, values in sim.timeseries()[key].items():
        reference = values[REFERENCE_DAYS]
        if None in reference:  # a good nobody produced in the window has no index
            assert set(values) == {None}, good
            continue
        assert sum(reference) / len(reference) == pytest.approx(100, abs=0.5), good


def test_index_waits_for_the_reference_window_and_skips_absent_goods():
    assert _index([5.0] * 14) == [None] * 14  # day 14 not reached yet
    assert _index([0.0] * 20) == [None] * 20  # nothing to compare against
    assert _index([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 4])[-1] == 200.0
