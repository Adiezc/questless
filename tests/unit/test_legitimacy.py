# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M48.1-M48.2: legitimacy falls with unpaid wages and hunger, recovers slowly, and NPCs evade the
levy while it is low, without any coin being created or destroyed."""

import dataclasses

import pytest

from questless.config import ConfigError, LegitimacyConfig, parse_scenario, to_dict
from questless.sim.entities import OUTSIDE, TOWN
from questless.sim.ledger import Asset
from questless.sim.world import build_world


def _on(cfg, **kw):
    return dataclasses.replace(cfg, legitimacy=LegitimacyConfig(enabled=True, **kw))


def _drain_town(world):
    coin = world.ledger.balance(TOWN, Asset.COIN)
    world.ledger.transfer(TOWN, OUTSIDE, Asset.COIN, coin, tick=world.tick, reason="test")


def test_off_by_default_and_hash_free(baseline):
    assert baseline.legitimacy.enabled is False
    world = build_world(baseline)
    world.step(20)
    assert all(s.legitimacy is None and s.levy_evaded == 0 for s in world.stats)
    assert "legitimacy" not in world.state_dict()


def test_unpaid_wages_lower_legitimacy_and_pay_restores_it(baseline):
    no_reserve = dataclasses.replace(baseline.town, reserve_days=0)  # #72 would refill it daily
    world = build_world(_on(dataclasses.replace(baseline, town=no_reserve)))
    world.step(10)
    assert world.legitimacy > 0.9
    for _ in range(7):  # a week with no money for guards
        _drain_town(world)
        world.step()
    low = world.legitimacy
    assert all(s.wages_unpaid for s in world.stats[-7:])  # the levy alone can't pay every guard
    assert low < 0.85  # falls fast...
    world.step(60)  # wages are paid again from the levy and market tax
    assert world.legitimacy > low + 0.1  # ...and recovers slowly
    assert all(0 <= s.legitimacy <= 1 for s in world.stats)
    world.check_invariants()


def test_low_legitimacy_means_levy_evasion_without_new_coin(baseline):
    world = build_world(_on(baseline, start=0.0, recover_rate=0.0, min_compliance=0.2))
    total = world.ledger.total(Asset.COIN)
    world.step(15)
    assert sum(s.levy_evaded for s in world.stats) > 0
    assert world.ledger.total(Asset.COIN) == total
    world.check_invariants()


def test_full_legitimacy_matches_the_levy_of_the_feature_off(baseline):
    """With legitimacy pinned at 1, everyone pays: the town collects exactly what it would."""
    off = build_world(baseline)
    on = build_world(_on(baseline, fall_rate=0.0))
    off.step(30)
    on.step(30)
    assert [s.upkeep for s in on.stats] == [s.upkeep for s in off.stats]
    assert sum(s.levy_evaded for s in on.stats) == 0


def test_legitimacy_replays_and_round_trips(baseline):
    cfg = _on(baseline, start=0.6)
    assert parse_scenario(to_dict(cfg)) == cfg
    a, b = build_world(cfg), build_world(cfg)
    a.step(40)
    b.step(40)
    assert a.state_hash() == b.state_hash()


@pytest.mark.parametrize(
    "table, message",
    [
        ({"enabled": "yes"}, "true or false"),
        ({"start": 1.5}, "between 0 and 1"),
        ({"hunger_window": 0}, "hunger_window"),
        ({"speed": 1}, "unknown keys"),
    ],
)
def test_bad_legitimacy_config_fails_loudly(baseline, table, message):
    raw = to_dict(baseline)
    raw["legitimacy"] = table
    with pytest.raises(ConfigError, match=message):
        parse_scenario(raw)


def test_spiral_scenario_traps_the_town_on_most_seeds():
    """M48.5: a town starting short of coin stays stuck: low legitimacy, evasion, unpaid wages."""
    from questless.config import load_scenario
    from tests.conftest import SCENARIOS

    cfg = load_scenario(SCENARIOS / "legitimacy_spiral.toml")
    trapped = 0
    for seed in range(1, 6):
        world = build_world(dataclasses.replace(cfg, seed=seed))
        world.step(90)
        late = world.stats[60:]
        trapped += (
            max(s.legitimacy for s in late) < 0.6
            and all(s.wages_unpaid for s in late)
            and sum(s.levy_evaded for s in late) > 0
        )
        world.check_invariants()
    assert trapped >= 4
