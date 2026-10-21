# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M6 acceptance: every contract explains itself with evidence that re-measures exactly, traced
back to root causes; cascades link contracts into a lineage."""

import dataclasses

import pytest

from questless.contracts.model import ContractKind
from questless.contracts.provenance import verify
from questless.sim.ledger import Asset
from questless.sim.world import build_world
from tests.conftest import bandits, drought, mine_collapse, with_shocks

SCENARIOS = {
    "mine_collapse": (mine_collapse(factor=0.1, duration=40),),  # deep enough to reach food
    "drought": (drought(),),
    "bandits": (bandits(),),
}


@pytest.fixture(scope="module")
def worlds():
    from questless.config import load_scenario
    from tests.conftest import SCENARIOS as DIR

    base = load_scenario(DIR / "baseline.toml")
    out = {}
    for name, shocks in SCENARIOS.items():
        world = build_world(with_shocks(base, *shocks))
        world.step(75)
        out[name] = world
    return out


@pytest.mark.parametrize("name", SCENARIOS)
def test_every_contract_has_verifiable_provenance(worlds, name):
    world = worlds[name]
    assert world.contracts.contracts
    for c in world.contracts.contracts.values():
        assert len(c.provenance.chain) >= 3, c.id
        assert verify(world, c) == [], c.id


@pytest.mark.parametrize("name", SCENARIOS)
def test_shock_scenarios_trace_back_to_their_shock(worlds, name):
    world = worlds[name]
    first = min(world.contracts.contracts.values(), key=lambda c: c.created_tick)
    roots = [e for e in first.provenance.roots() if e.kind == "shock"]
    assert roots, [e.kind for e in first.provenance.chain]
    assert roots[0].tick == SCENARIOS[name][0].start


def test_mine_collapse_cascade_reaches_food_through_tools(worlds):
    """Mine collapse -> ore drop -> idle smiths -> tools drop -> farmers without tools -> food."""
    world = worlds["mine_collapse"]
    food = [c for c in world.contracts.contracts.values() if c.good is Asset.FOOD]
    cascades = [
        c
        for c in food
        if {"production_drop", "input_shortage", "equipment_shortage", "shock"}
        <= {e.kind for e in c.provenance.chain}
    ]
    assert cascades, "no food contract traced back through the tools shortage"
    subjects = {e.subject for e in cascades[0].provenance.chain}
    assert {"site:mine", "production:iron_ore", "production:tools", "production:food"} <= subjects


def test_cascade_contracts_form_a_lineage(worlds):
    board = worlds["mine_collapse"].contracts
    linked = [c for c in board.contracts.values() if c.parent_id]
    assert linked
    child = linked[0]
    parent = board.contracts[child.parent_id]
    assert parent.created_tick < child.created_tick
    assert parent.good is not child.good  # the parent is upstream, not a repost
    assert child.id in board.children(parent.id)
    assert board.ancestors(child.id)[0] == parent.id


def test_transport_contract_blames_the_road(worlds):
    world = worlds["bandits"]
    transport = [c for c in world.contracts.contracts.values() if c.kind is ContractKind.TRANSPORT]
    assert transport
    assert any(e.subject == "road:transport" for e in transport[0].provenance.roots())


def test_baseline_contracts_cite_no_shock(baseline):
    world = build_world(baseline)
    world.step(365)
    for c in world.contracts.contracts.values():
        assert all(e.kind != "shock" for e in c.provenance.chain)


def test_tampered_evidence_is_detected(worlds):
    world = worlds["mine_collapse"]
    c = next(iter(world.contracts.contracts.values()))
    measured = next(i for i, e in enumerate(c.provenance.chain) if e.measure)
    chain = list(c.provenance.chain)
    chain[measured] = dataclasses.replace(chain[measured], value=chain[measured].value + 1)
    forged = dataclasses.replace(
        c, provenance=dataclasses.replace(c.provenance, chain=tuple(chain))
    )
    assert verify(world, forged)


def test_rendered_explanation_uses_names_and_numbers(worlds):
    world = worlds["drought"]
    names = {n.id: n.name for n in world.npcs.values()}
    c = next(c for c in world.contracts.contracts.values() if c.kind is ContractKind.TOWN_SUPPLY)
    lines = c.provenance.render(names)
    assert lines[0].startswith("Day 20: The farms")
    assert not any("npc_" in line for line in lines)
