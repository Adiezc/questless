# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
import copy
import tomllib

import pytest

from questless.config import ConfigError, load_scenario, parse_scenario
from questless.sim.entities import Profession, Site
from questless.sim.ledger import Asset
from tests.conftest import SCENARIOS


@pytest.fixture
def raw() -> dict:
    with (SCENARIOS / "baseline.toml").open("rb") as fh:
        return tomllib.load(fh)


def test_baseline_loads_with_100_npcs(baseline):
    assert baseline.population == 100
    assert baseline.professions[Profession.MINER].site is Site.MINE
    assert baseline.goods[Asset.TOOLS].base_price == 24
    assert set(baseline.guilds) == {"miners", "merchants", "blacksmiths"}


def _broken(raw: dict, mutate) -> dict:
    data = copy.deepcopy(raw)
    mutate(data)
    return data


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d["scenario"].update(sede=1), "unknown keys"),
        (lambda d: d["professions"]["miner"].update(site="moon"), "not one of"),
        (lambda d: d["professions"]["miner"].update(wallet=[100, 50]), "low <= high"),
        (lambda d: d["professions"]["miner"].update(count=-1), ">= 0"),
        (lambda d: d["professions"]["miner"]["inventory"].update(coin=5), "coin is set via"),
        (lambda d: d["guilds"]["miners"].update(professions=["farmer"]), "already belongs"),
        (lambda d: d["goods"]["food"].update(price_floor=2.0), "price_floor"),
        (lambda d: d["town"].update(market_tax=1.5), "between 0 and 1"),
        (lambda d: d.pop("traits"), "missing"),
        (lambda d: d["professions"]["guard"].update(equipment="coin"), "coin is not a good"),
        (lambda d: d["professions"]["blacksmith"].update(recipes={}), "no recipes"),
        (
            lambda d: d.update(
                shocks=[
                    {"name": "x", "effect": "site_output", "start": 0, "duration": 1, "factor": 0.5}
                ]
            ),
            "need a site",
        ),
    ],
)
def test_invalid_configs_fail_loudly(raw, mutate, message):
    with pytest.raises(ConfigError, match=message):
        parse_scenario(_broken(raw, mutate))


def _shock(factor):
    return [
        {"name": "x", "effect": "transport_capacity", "start": 0, "duration": 1, "factor": factor}
    ]


@pytest.mark.parametrize(
    "mutate",
    [
        # _at_least: `v < minimum` is False for nan and for inf, so both slipped through
        lambda d: d.update(shocks=_shock(float("nan"))),
        lambda d: d.update(shocks=_shock(float("inf"))),
        lambda d: d["contracts"].update(npc_premium=float("inf")),
        lambda d: d["player"].update(caravan_markup=float("nan")),
        # an int too large to become a float used to escape as OverflowError
        lambda d: d["contracts"].update(npc_premium=10**400),
        # _fraction and _float_range rejected these by accident, with the wrong message
        lambda d: d["town"].update(market_tax=float("nan")),
        lambda d: d["traits"].update(skill=[float("nan"), 1.0]),
        lambda d: d["market"].update(effort=[0.5, float("inf")]),
    ],
)
def test_non_finite_numbers_are_rejected(raw, mutate):
    with pytest.raises(ConfigError, match="must be a finite number"):
        parse_scenario(_broken(raw, mutate))


@pytest.mark.parametrize("token", ["nan", "inf", "-inf"])
def test_non_finite_toml_floats_are_rejected(tmp_path, token):
    """A literal `factor = nan` in a scenario file fails to load instead of poisoning the run."""
    path = tmp_path / "non_finite.toml"
    path.write_text(
        (SCENARIOS / "baseline.toml").read_text(encoding="utf-8")
        + '\n[[shocks]]\nname = "x"\neffect = "transport_capacity"\n'
        + f"start = 10\nduration = 20\nfactor = {token}\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match=r"shocks\[0\]\.factor: must be a finite number"):
        load_scenario(path)
