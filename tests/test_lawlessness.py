from pathlib import Path

from questless.api import Simulation
from questless.contracts.provenance import measure


def test_lawlessness_index_metric():
    sim = Simulation.from_scenario(Path("scenarios/baseline.toml"), seed=42)
    sim.step(15)

    # In baseline with 0 contraband trade, lawlessness is 0.0
    val = measure(sim.world, ("lawlessness", 30), 14)
    assert val == 0.0

    # Injecting simulated contraband stats
    sim.world.stats[14].smuggled_volume = 25
    sim.world.stats[14].lost_tax = 10

    val_updated = measure(sim.world, ("lawlessness", 30), 14)
    assert val_updated == 35.0
