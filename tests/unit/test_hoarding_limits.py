# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""#93: a player learns of a shock only when it starts, and can buy at most a share of a good's
stock each day, so nobody can corner the ore the moment a mine collapses. The schedule stays in
the engine (and in saves), so runs replay exactly."""

import copy
import dataclasses

import pytest

from questless import player
from questless.api import Simulation
from questless.config import ConfigError, parse_scenario, to_dict
from questless.player import ActionError
from questless.sim.ledger import Asset
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


def _bought(sim, good):
    return sim.player()["goods"].get(good, 0)


def test_player_buys_at_most_a_quarter_of_the_days_stock():
    sim = Simulation.from_scenario(SCENARIOS / "iron_shortage.toml")
    sim.step(5)
    on_offer = sum(units for _, units in player._asks(sim.world, Asset.FOOD))
    first = sim.buy("food", 10_000)
    assert first == max(int(0.25 * on_offer), 1)
    with pytest.raises(ActionError, match="today's share"):
        sim.buy("food", 1)  # a second order the same day gets nothing more
    sim.step()
    assert sim.buy("food", 1) == 1  # the allowance resets each day
    assert _bought(sim, "food") == first + 1


def test_without_a_cap_the_player_can_buy_all_the_stock(baseline):
    sim = Simulation.from_scenario(dataclasses.replace(baseline, max_buy_share=1.0))
    sim.step(5)
    on_offer = sum(units for _, units in player._asks(sim.world, Asset.FOOD))
    affordable = sim.player()["coin"] // max(1, round(sim.prices()["food"]))
    assert sim.buy("food", 10_000) == min(on_offer, affordable)


@pytest.mark.parametrize("share", [0, -0.1, 1.5])
def test_bad_buy_share_fails_loudly(baseline, share):
    raw = copy.deepcopy(to_dict(baseline))
    raw["player"]["max_buy_share"] = share
    with pytest.raises(ConfigError, match="max_buy_share"):
        parse_scenario(raw)


def test_buy_share_round_trips_through_saves(baseline):
    assert baseline.max_buy_share == 0.25
    assert parse_scenario(to_dict(baseline)) == baseline
