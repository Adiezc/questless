# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M15.2: each measured chain step can be charted, and the chart passes through the recorded value.
Needs the dashboard extra (plotly); skipped on a bare install."""

import sys
from pathlib import Path

import pytest

pytest.importorskip("plotly")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))

import charts  # noqa: E402

from questless.api import Simulation  # noqa: E402
from tests.conftest import SCENARIOS  # noqa: E402


@pytest.fixture(scope="module")
def sim():
    sim = Simulation.from_scenario(SCENARIOS / "iron_shortage.toml")
    sim.step(45)
    return sim


def test_every_measured_step_charts_through_its_recorded_value(sim):
    checked = 0
    for c in sim.contracts():
        for i, ev in enumerate(c.provenance.chain):
            if ev.measure is None:
                continue
            fig = charts.evidence_chart(sim, c, i)
            line, point = fig.data[0], fig.data[1]
            tick = ev.measure[1]
            assert list(point.x) == [tick]
            assert point.y[0] == pytest.approx(ev.value)
            assert dict(zip(line.x, line.y, strict=True))[tick] == pytest.approx(ev.value)
            lines = {s.y0 for s in fig.layout.shapes if s.y0 == s.y1}  # horizontal references
            for ref in (ev.baseline, ev.threshold):
                if ref is not None:
                    assert ref in lines
            checked += 1
    assert checked >= 3, "too few measured steps to prove anything"


def test_default_step_prefers_the_output_drop(sim):
    c = sim.contracts()[0]
    chain = c.provenance.chain
    steps = [i for i, e in enumerate(chain) if e.measure]
    assert chain[charts.default_step(chain, steps)].kind == "production_drop"
    assert charts.default_step(chain, []) is None


def test_small_multiples_creates_four_subplots_with_traces():
    series = {
        "day": [0, 1, 2, 3],
        "produced": {
            "food": [10, 12, 11, 13],
            "iron_ore": [5, 4, 3, 2],
            "tools": [2, 2, 3, 3],
            "weapons": [1, 1, 1, 2],
        },
    }
    shocks = []
    fig = charts.small_multiples(series, "produced", "Production per day", shocks)
    assert len(fig.data) == 4
    # Check trace names match good labels
    trace_names = [t.name for t in fig.data]
    assert trace_names == ["Food", "Iron ore", "Tools", "Weapons"]
    # Check trace colors match GOOD_COLORS
    for trace, good in zip(fig.data, ["food", "iron_ore", "tools", "weapons"], strict=True):
        assert trace.line.color == charts.GOOD_COLORS[good]
        assert list(trace.x) == [0, 1, 2, 3]
        assert list(trace.y) == series["produced"][good]
    # Check 4 subplots exist in layout
    assert hasattr(fig.layout, "xaxis")
    assert hasattr(fig.layout, "xaxis2")
    assert hasattr(fig.layout, "xaxis3")
    assert hasattr(fig.layout, "xaxis4")
    assert hasattr(fig.layout, "yaxis")
    assert hasattr(fig.layout, "yaxis2")
    assert hasattr(fig.layout, "yaxis3")
    assert hasattr(fig.layout, "yaxis4")


def test_small_multiples_index_and_percent_modes():
    series = {
        "day": [0, 1, 2],
        "rate": {
            "food": [100.0, 95.0, 90.0],
            "iron_ore": [100.0, 50.0, 30.0],
            "tools": [100.0, 100.0, 100.0],
            "weapons": [100.0, 80.0, 70.0],
        },
    }
    fig_idx = charts.small_multiples(series, "rate", "Rate Index", [], index=True)
    # Check 100% reference line exists across subplots
    hlines = [s for s in fig_idx.layout.shapes if s.y0 == 100 and s.y1 == 100]
    assert len(hlines) == 4

    fig_pct = charts.small_multiples(series, "rate", "Rate Percent", [], percent=True)
    assert list(fig_pct.layout.yaxis.range) == [-3, 103]
    assert list(fig_pct.layout.yaxis4.range) == [-3, 103]
