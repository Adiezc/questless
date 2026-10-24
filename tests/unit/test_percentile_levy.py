# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Levy brackets that follow the wealth distribution: each day's threshold is the NPC wallet at a
percentile, so the bracket keeps taxing the richest NPCs however much coin they hold."""

import copy
import dataclasses
import tomllib

import pytest

from questless.config import ConfigError, parse_scenario, to_dict
from questless.sim.world import build_world
from tests.conftest import SCENARIOS

TOP = [{"percentile": 0.9, "rate": 0.06}, {"percentile": 0.99, "rate": 0.10}]


@pytest.fixture
def raw() -> dict:
    with (SCENARIOS / "baseline.toml").open("rb") as fh:
        return tomllib.load(fh)


def _with(raw: dict, brackets) -> dict:
    raw = copy.deepcopy(raw)
    raw["town"]["levy_brackets"] = brackets
    return raw


def test_percentiles_resolve_to_the_wallet_at_that_rank(raw):
    town = parse_scenario(_with(raw, TOP)).town
    assert town.levy_brackets == ()
    wallets = list(range(1, 201))  # 1..200: nearest-rank p90 is 180, p99 is 198
    assert town.brackets_for(wallets) == ((180, 0.06), (198, 0.10))
    assert town.brackets_for(list(reversed(wallets))) == town.brackets_for(wallets)


def test_thresholds_stay_above_the_exemption_and_each_other(raw):
    town = parse_scenario(_with(raw, TOP)).town
    exempt = town.upkeep_exempt
    assert town.brackets_for([5] * 50) == ((exempt + 1, 0.06), (exempt + 2, 0.10))
    assert town.brackets_for([]) == ((exempt + 1, 0.06), (exempt + 2, 0.10))


def test_fixed_brackets_are_unchanged(raw):
    town = parse_scenario(_with(raw, [{"threshold": 500, "rate": 0.05}])).town
    assert town.brackets_for([1, 2, 3]) == ((500, 0.05),)


@pytest.mark.parametrize(
    "brackets, message",
    [
        ([{"percentile": 0.9, "rate": 0.05}, {"threshold": 900, "rate": 0.1}], "not both"),
        ([{"percentile": 1.0, "rate": 0.05}], "between 0.0 and 1"),
        ([{"percentile": 0.9, "rate": 0.05}, {"percentile": 0.5, "rate": 0.1}], "between 0.9"),
        ([{"percentile": 0.9}], "missing"),
    ],
)
def test_bad_percentile_brackets_fail_loudly(raw, brackets, message):
    with pytest.raises(ConfigError, match=message):
        parse_scenario(_with(raw, brackets))


def test_percentile_brackets_round_trip_through_saves(raw):
    cfg = parse_scenario(_with(raw, TOP))
    assert parse_scenario(to_dict(cfg)) == cfg


def test_the_top_decile_pays_more_and_holds_less(raw):
    cfg = parse_scenario(_with(raw, TOP))
    world = build_world(cfg)
    flat = build_world(
        dataclasses.replace(cfg, town=dataclasses.replace(cfg.town, levy_percentiles=()))
    )
    world.step(60)
    flat.step(60)
    world.check_invariants()
    assert all(len(s.levy_thresholds) == 2 for s in world.stats)
    assert all(s.levy_thresholds == () for s in flat.stats)
    assert world.stats[0].upkeep > flat.stats[0].upkeep  # same wallets, steeper top
    assert world.stats[-1].coin_top10_share < flat.stats[-1].coin_top10_share
