# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M13.6: a summary must attribute the quoted numbers to the evidence's good."""

from types import SimpleNamespace

import pytest

from questless.config import load_scenario
from questless.contracts.model import Contract, ContractKind
from questless.contracts.provenance import Evidence, Provenance, _num
from questless.contracts.summary import summarise
from questless.sim.ledger import Asset
from questless.sim.world import build_world
from tests.conftest import SCENARIOS

MIDDLE_CASES = (
    ("production_drop", "production", "Iron ore output fell to 3/day from 12."),
    ("transport_backlog", "sites", "3 iron ore sat waiting at the sites."),
    ("price_spike", "market", "The iron ore price rose to 3 from 12."),
    ("unfilled_demand", "market", "3 iron ore went unsold to buyers who could pay."),
)


def contract_with(*chain):
    return Contract(
        id="C-0001",
        kind=ContractKind.PROCUREMENT,
        requester="npc_001",
        funder="npc_001",
        good=Asset.IRON_ORE,
        qty=5,
        beneficiaries={"npc_001": 5},
        reward=20,
        rep_reward=1,
        created_tick=30,
        deadline_tick=40,
        dedup_key=("npc_001", "procurement", "iron_ore"),
        provenance=Provenance(tuple(chain), "synthetic"),
        reason="",
    )


@pytest.mark.parametrize("kind,prefix,expected", MIDDLE_CASES)
def test_summary_prefers_the_contracts_good(kind, prefix, expected):
    upstream = Evidence(30, kind, f"{prefix}:tools", "units", 2, baseline=7.07)
    own = Evidence(30, kind, f"{prefix}:iron_ore", "units", 3, baseline=12)
    assert summarise(SimpleNamespace(), contract_with(upstream, own)) == expected


@pytest.mark.parametrize("kind,prefix,expected", MIDDLE_CASES)
def test_summary_fallback_labels_the_evidences_good(kind, prefix, expected):
    upstream = Evidence(30, kind, f"{prefix}:iron_ore", "units", 3, baseline=12)
    contract = contract_with(upstream)
    contract.good = Asset.FOOD
    assert summarise(SimpleNamespace(), contract) == expected


def test_own_good_takes_precedence_over_an_upstream_preferred_kind():
    upstream = Evidence(30, "production_drop", "production:tools", "units", 2, baseline=7.07)
    own = Evidence(30, "price_spike", "market:iron_ore", "price", 3, baseline=12)
    assert summarise(SimpleNamespace(), contract_with(upstream, own)) == (
        "The iron ore price rose to 3 from 12."
    )


def test_middle_kind_priority_is_preserved_for_the_same_good():
    price = Evidence(30, "price_spike", "market:iron_ore", "price", 4, baseline=1)
    production = Evidence(30, "production_drop", "production:iron_ore", "units", 3, baseline=12)
    assert summarise(SimpleNamespace(), contract_with(price, production)) == (
        "Iron ore output fell to 3/day from 12."
    )


@pytest.mark.parametrize("scenario", sorted(SCENARIOS.glob("*.toml")), ids=lambda p: p.stem)
def test_scenario_summary_numbers_belong_to_the_named_good(scenario):
    world = build_world(load_scenario(scenario))
    world.step(150)
    checked = 0
    for contract in world.contracts.contracts.values():
        text = summarise(world, contract)
        # Compare each possible middle sentence with its source record. Unlike the old number
        # membership test, this requires the good and all quoted values to match together.
        candidates = []
        for evidence in contract.provenance.chain:
            good = evidence.subject.partition(":")[2].replace("_", " ")
            value = _num(evidence.value)
            baseline = _num(evidence.baseline) if evidence.baseline is not None else "?"
            sentences = {
                "production_drop": (
                    f"{good.capitalize()} output fell to {value}/day from {baseline}."
                ),
                "transport_backlog": f"{value} {good} sat waiting at the sites.",
                "price_spike": f"The {good} price rose to {value} from {baseline}.",
                "unfilled_demand": f"{value} {good} went unsold to buyers who could pay.",
            }
            if evidence.kind in sentences:
                candidates.append((evidence.subject.partition(":")[2], sentences[evidence.kind]))
        if candidates:
            own = [sentence for good, sentence in candidates if good == str(contract.good)]
            assert any(sentence in text for sentence in own or [s for _, s in candidates]), (
                contract.id,
                text,
            )
            checked += 1
    assert checked, "scenario produced no contract summaries"
