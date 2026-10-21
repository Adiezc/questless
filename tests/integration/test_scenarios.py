# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Scenarios A and B are reproducible across seeds, not just on the demo seed."""

import pytest

from questless.api import Simulation
from questless.contracts.model import ContractKind
from questless.sim.ledger import Asset
from tests.conftest import SCENARIOS

SEEDS = [1, 2, 3, 4, 5]
SHOCK_DAY = 15


def _run(name, seed, days=60):
    sim = Simulation.from_scenario(SCENARIOS / f"{name}.toml", seed=seed)
    sim.step(days)
    return sim


@pytest.mark.parametrize("seed", SEEDS)
def test_scenario_a_iron_shortage(seed):
    sim = _run("iron_shortage", seed)
    iron = [c for c in sim.contracts() if c.good is Asset.IRON_ORE]
    assert iron, "no iron contract"
    first = min(c.created_tick for c in iron)
    assert SHOCK_DAY < first <= SHOCK_DAY + 15
    assert any(c.funder == "guild:blacksmiths" for c in iron)
    root = sim.contract(min(iron, key=lambda c: c.created_tick).id).provenance.roots()[0]
    assert root.kind == "shock" and root.subject == "site:mine"


@pytest.mark.parametrize("seed", SEEDS)
def test_scenario_b_drought(seed):
    sim = _run("drought", seed)
    food = [c for c in sim.contracts() if c.good is Asset.FOOD]
    assert food, "no food contract"
    first = min(c.created_tick for c in food)
    assert SHOCK_DAY < first <= SHOCK_DAY + 15
    pooled = {c.kind for c in food} & {ContractKind.TOWN_SUPPLY, ContractKind.GUILD_SUPPLY}
    assert pooled, "no pooled emergency supply"
    assert any(e.subject == "site:farms" for c in food for e in c.provenance.roots())


@pytest.mark.parametrize("seed", SEEDS)
def test_baseline_stays_quiet(seed):
    sim = _run("baseline", seed, days=120)
    assert len(sim.contracts()) <= 4
