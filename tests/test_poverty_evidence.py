from pathlib import Path

from questless.api import Simulation
from questless.contracts.provenance import Evidence, measure


def test_poverty_evidence_measure_and_rendering():
    sim = Simulation.from_scenario(Path("scenarios/baseline.toml"), seed=42)
    sim.step(10)

    val = measure(sim.world, ("unaffordable", "iron_ore", 7), 9)
    assert val >= 0.0

    ev = Evidence(
        tick=9,
        kind="poverty",
        subject="market:iron_ore",
        metric="7 days",
        value=val,
        baseline=0.0,
        measure=(("unaffordable", "iron_ore", 7), 9),
    )
    rendered = ev.render()
    assert "Market for iron ore had" in rendered
    assert "unaffordable demand over 7 days" in rendered
