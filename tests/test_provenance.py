# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M6 acceptance: every contract explains itself with evidence that re-measures exactly, traced
back to root causes; cascades link contracts into a lineage."""

import dataclasses
import re

import pytest

from questless.config import ShockConfig, ShockEffect
from questless.contracts.model import ContractKind
from questless.contracts.provenance import _num, measure, series, verify
from questless.contracts.summary import summarise
from questless.sim.entities import Site
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


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_m15_1_series_agrees_with_every_measured_step(worlds, name):
    """M15.1 acceptance: a chart built from ``series`` shows exactly the numbers in the chain,
    for every measured value and baseline of every contract."""
    world = worlds[name]
    checked = 0
    for c in world.contracts.contracts.values():
        for e in c.provenance.chain:
            for recorded, m in ((e.value, e.measure), (e.baseline, e.baseline_measure)):
                if m is None:
                    continue
                key, tick = m
                assert series(world, key, tick - 3, tick + 3)[tick] == pytest.approx(recorded)
                checked += 1
    assert checked, f"{name} produced no measured evidence"


def test_m15_1_series_covers_recorded_days_only(worlds):
    world = worlds["drought"]
    days = series(world, ("transport_factor",), -5)
    assert list(days) == list(range(len(world.stats)))  # clamped to what was recorded
    assert series(world, ("transport_factor",), 10, 12) == {
        t: measure(world, ("transport_factor",), t) for t in (10, 11, 12)
    }


def test_m15_1_simulation_evidence_series():
    from questless.api import Simulation
    from tests.conftest import SCENARIOS as DIR

    sim = Simulation.from_scenario(DIR / "iron_shortage.toml")
    sim.step(40)
    c = next(c for c in sim.contracts() if any(e.measure for e in c.provenance.chain))
    for i, e in enumerate(c.provenance.chain):
        if e.measure is None:
            with pytest.raises(ValueError, match="not a measured value"):
                sim.evidence_series(c.id, i)
        else:
            assert sim.evidence_series(c.id, i)[e.measure[1]] == pytest.approx(e.value)


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_m16_1_summary_only_repeats_numbers_from_the_chain(worlds, name):
    """M16.1: every number in a summary was recorded in the chain (or is the contract's qty)."""
    world = worlds[name]
    assert world.contracts.contracts
    for c in world.contracts.contracts.values():
        text = summarise(world, c)
        assert text.endswith("."), c.id
        allowed = {str(c.qty)}
        for e in c.provenance.chain:
            allowed.add(str(e.tick))
            allowed |= {_num(v) for v in (e.value, e.baseline, e.threshold) if v is not None}
        assert set(re.findall(r"\d+(?:\.\d+)?", text)) <= allowed, (c.id, text)
        assert f"{c.reward} coin" in text, (c.id, text)


def _shock_roots(contracts):
    """(contract, cited shock evidence) for every contract, in chain order."""
    return [(c, [e for e in c.provenance.chain if e.kind == "shock"]) for c in contracts]


@pytest.mark.parametrize(
    "earlier",
    [
        ShockConfig("Rich seam", ShockEffect.SITE_OUTPUT, 10, 10, 3.0, Site.MINE),
        mine_collapse(start=5, duration=8),
    ],
    ids=["boom", "expired_collapse"],
)
def test_only_shocks_that_cut_output_and_overlap_are_cited(earlier):
    """#47: a boom, or a collapse that ended weeks before, is never blamed for later bandits."""
    from questless.config import load_scenario
    from tests.conftest import SCENARIOS as DIR

    world = build_world(
        with_shocks(load_scenario(DIR / "baseline.toml"), earlier, bandits(start=50))
    )
    world.step(85)
    later = [c for c in world.contracts.contracts.values() if c.created_tick >= 50]
    assert later
    for c, shocks in _shock_roots(later):
        assert all(e.value < 1 for e in shocks), (c.id, shocks)
        assert all(e.tick != earlier.start for e in shocks), (c.id, shocks)
        if c.kind is ContractKind.TRANSPORT:
            assert shocks and shocks[0].tick == 50, c.id
        assert verify(world, c) == [], c.id
    summaries = [summarise(world, c) for c in later if c.kind is ContractKind.TRANSPORT]
    assert summaries and not any(earlier.name in s for s in summaries)
