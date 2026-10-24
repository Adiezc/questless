# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M58.1: how unequal NPC coin is (Gini, top-10% share), one value per day."""

import pytest

from questless.api import Simulation
from questless.metrics import gini, top_share
from tests.conftest import SCENARIOS


def test_gini_is_zero_when_everyone_holds_the_same():
    assert gini([7, 7, 7, 7]) == 0.0


@pytest.mark.parametrize("n", [2, 5, 10, 120])
def test_gini_of_one_holder_is_n_minus_one_over_n(n):
    assert gini([0] * (n - 1) + [100]) == pytest.approx((n - 1) / n)


def test_gini_is_zero_for_empty_or_all_zero():
    assert gini([]) == 0.0
    assert gini([0, 0, 0]) == 0.0


def test_gini_ignores_input_order():
    assert gini([5, 1, 9, 3]) == gini([1, 3, 5, 9])


def test_top_share_takes_the_richest_tenth():
    assert top_share([1] * 9 + [91]) == pytest.approx(0.91)
    assert top_share([10] * 20) == pytest.approx(0.1)  # 2 of 20 hold 20 of 200
    assert top_share([3]) == 1.0
    assert top_share([]) == 0.0
    assert top_share([0, 0]) == 0.0


def test_baseline_series_have_one_value_per_day_in_range():
    sim = Simulation.from_scenario(SCENARIOS / "baseline.toml")
    sim.step(30)
    series = sim.timeseries()
    for key in ("coin_gini", "coin_top10_share"):
        assert len(series[key]) == len(series["day"]) == 30, key
        assert all(0.0 <= v <= 1.0 for v in series[key]), key
    assert any(v > 0 for v in series["coin_gini"]), "every wallet equal all month is suspicious"
