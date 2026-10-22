# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M14.4: unmet demand as a share of demand, so goods with different volumes share one axis."""

from questless.api import Simulation
from questless.metrics import _unfilled_pct
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
