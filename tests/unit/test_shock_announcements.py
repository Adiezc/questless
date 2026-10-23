# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""#93: a player learns of a shock only when it starts. The schedule stays in the engine (and in
saves), so the run itself is unchanged."""

from questless.api import Simulation
from tests.conftest import SCENARIOS


def test_player_sees_no_shock_before_it_starts():
    sim = Simulation.from_scenario(SCENARIOS / "iron_shortage.toml")  # mine collapses day 15-44
    assert sim.config.shocks == ()
    assert sim.world.config.shocks  # the engine still runs it
    sim.step(14)
    assert sim.shocks() == []
    sim.step()
    (news,) = sim.shocks()
    assert news == {
        "name": "Mine collapse",
        "effect": "site_output",
        "site": "mine",
        "started": 15,
        "ended": None,  # how long it lasts isn't announced
    }
    sim.step(30)
    assert sim.shocks()[0]["ended"] == 45


def test_user_shocks_are_announced_like_scenario_ones():
    sim = Simulation.from_scenario(SCENARIOS / "baseline.toml")
    sim.step(3)
    sim.shock("site_output", 0.5, 5, "Flood", site="farms")
    assert [s["name"] for s in sim.shocks()] == ["Flood"]


def test_saves_keep_the_full_schedule_and_replay_exactly(tmp_path):
    sim = Simulation.from_scenario(SCENARIOS / "iron_shortage.toml")
    sim.step(5)  # saved before the shock is announced
    loaded = Simulation.load(sim.save(tmp_path / "save.json"))
    assert loaded.world.config.shocks == sim.world.config.shocks
    sim.step(20)
    loaded.step(20)
    assert loaded.world.state_hash() == sim.world.state_hash()
    assert loaded.shocks() and loaded.shocks() == sim.shocks()
