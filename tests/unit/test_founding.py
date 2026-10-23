# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M54.1: colonies inherit their parent's institutions, changed only within declared bounds."""

import copy
import random
import tomllib

import pytest

from questless.config import ConfigError, parse_scenario, to_dict
from questless.founding import mutate, mutations
from tests.conftest import SCENARIOS

BOUNDS = {
    "town.upkeep_rate": [0.01, 0.06],
    "town.guard_wage": [5, 9],
    "guilds.*.dues_rate": [0.02, 0.1],
    "guilds.miners.policy.relief_days": [0, 4],
}


@pytest.fixture
def raw() -> dict:
    with (SCENARIOS / "baseline.toml").open("rb") as fh:
        data = tomllib.load(fh)
    data["founding"] = {"bounds": copy.deepcopy(BOUNDS)}
    return data


@pytest.fixture
def parent(raw):
    return parse_scenario(raw)


def _knob_values(cfg):
    d = to_dict(cfg)
    yield "town.upkeep_rate", d["town"]["upkeep_rate"]
    yield "town.guard_wage", d["town"]["guard_wage"]
    for g in d["guilds"].values():
        yield "guilds.*.dues_rate", g["dues_rate"]
    yield "guilds.miners.policy.relief_days", d["guilds"]["miners"]["policy"]["relief_days"]


def test_colonies_stay_within_bounds_over_many_generations(parent):
    rng = random.Random("questless:1:founding")
    cfg = parent
    for _ in range(50):
        cfg = mutate(cfg, rng)
        for knob, value in _knob_values(cfg):
            low, high = BOUNDS[knob]
            assert low <= value <= high, (knob, value)
    assert isinstance(to_dict(cfg)["town"]["guard_wage"], int)


def test_only_listed_knobs_change(parent):
    child = mutate(parent, random.Random(7))
    changed = mutations(parent, child)
    assert changed  # something moved
    a, b = to_dict(parent), to_dict(child)
    for d in (a, b):
        d["town"].pop("upkeep_rate"), d["town"].pop("guard_wage")
        for g in d["guilds"].values():
            g.pop("dues_rate")
        d["guilds"]["miners"]["policy"].pop("relief_days")
    assert a == b


def test_same_rng_gives_the_same_colony(parent):
    assert mutate(parent, random.Random(3)) == mutate(parent, random.Random(3))
    assert mutate(parent, random.Random(3)) != mutate(parent, random.Random(4))


def test_colony_configs_round_trip(parent):
    child = mutate(parent, random.Random(11))
    assert parse_scenario(to_dict(child)) == child
    assert child.founding_bounds == parent.founding_bounds


def test_no_bounds_means_no_change(parent):
    import dataclasses

    plain = dataclasses.replace(parent, founding_bounds=())
    assert mutate(plain, random.Random(1)) == plain


@pytest.mark.parametrize(
    "bounds, message",
    [
        ({"contracts.deadline_days": [5, 10]}, "not a knob a colony may change"),
        ({"guilds.pirates.dues_rate": [0.0, 0.1]}, "unknown guild"),
        ({"town.guard_wage": [9, 5]}, "low must not exceed high"),
        ({"town.guard_wage": [5]}, r"expected \[low, high\]"),
    ],
)
def test_bad_bounds_fail_loudly(raw, bounds, message):
    raw["founding"] = {"bounds": bounds}
    with pytest.raises(ConfigError, match=message):
        parse_scenario(raw)
