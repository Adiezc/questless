# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M28.1-M28.2: bug reports carry a save and a checkable observation, and replay themselves."""

import json

import pytest

from questless import bugreport
from questless.api import Simulation
from questless.cli import main
from tests.conftest import SCENARIOS


@pytest.fixture(scope="module")
def sim():
    s = Simulation.from_scenario(SCENARIOS / "iron_shortage.toml")
    s.step(40)
    return s


def _seen(sim, op="=="):
    price = sim.world.stats[30].prices
    tools = round(price[next(a for a in price if str(a) == "tools")], 2)
    return {"metric": ["price", "tools"], "tick": 30, "op": op, "value": tools}


def test_report_reproduces_what_the_reporter_saw(sim):
    report = bugreport.write(sim.world, "tools price looks wrong", _seen(sim))
    report = json.loads(json.dumps(report))  # survives being saved as a file
    outcome = bugreport.repro(report)
    assert outcome.status == bugreport.REPRODUCED
    assert outcome.value == report["observation"]["value"]


def test_fixed_behaviour_reports_not_reproduced(sim):
    observation = {**_seen(sim), "op": "!="}  # "the price was not this": false on replay
    outcome = bugreport.repro(sim.bug_report("price differs", observation))
    assert outcome.status == bugreport.NOT_REPRODUCED


def test_tampered_save_reports_replay_mismatch(sim):
    report = sim.bug_report("anything", _seen(sim))
    report["save"]["state_hash"] = "0" * 64
    assert bugreport.repro(report).status == bugreport.REPLAY_MISMATCH


def test_report_without_observation_just_replays(sim):
    assert bugreport.repro(sim.bug_report("just a save")).status == bugreport.NO_OBSERVATION


@pytest.mark.parametrize(
    "bad, message",
    [
        ({"metric": ["vibes"], "tick": 3, "op": ">", "value": 1}, "unknown metric"),
        ({"metric": ["price", "tools"], "tick": 3, "op": "~", "value": 1}, "unknown operator"),
        ({"metric": ["price", "tools"], "tick": 999, "op": ">", "value": 1}, "isn't recorded"),
    ],
)
def test_bad_observations_are_rejected_when_writing(sim, bad, message):
    with pytest.raises(ValueError, match=message):
        sim.bug_report("bad", bad)


def test_repro_command_exit_codes(sim, tmp_path, capsys):
    path = tmp_path / "bug.json"
    path.write_text(json.dumps(sim.bug_report("tools", _seen(sim))))
    assert main(["repro", str(path)]) == 1
    assert "reproduced" in capsys.readouterr().out
    path.write_text(json.dumps(sim.bug_report("tools", {**_seen(sim), "op": "!="})))
    assert main(["repro", str(path)]) == 0
