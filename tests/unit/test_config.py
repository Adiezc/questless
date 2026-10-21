# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
import copy
import tomllib

import pytest

from questless.config import ConfigError, parse_scenario
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
    assert baseline.goods[Asset.TOOLS].base_price == 30
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
    ],
)
def test_invalid_configs_fail_loudly(raw, mutate, message):
    with pytest.raises(ConfigError, match=message):
        parse_scenario(_broken(raw, mutate))
