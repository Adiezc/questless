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
