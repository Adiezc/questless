"""Tests for M13.7: Don't fund a member twice through pool & individual contract (Fixes #45)."""

import pytest

from questless.api import Simulation
from questless.contracts.model import ContractKind
from questless.contracts.validation import ContractInvariantError, check_board
from tests.conftest import SCENARIOS


def test_no_member_funded_twice_by_pool_and_individual_contract():
    """Verify that in Iron Shortage (where individual procurement contracts are posted for tools),
    subsequently posted pooled contracts omit members who already have a live individual procurement
    contract for that good.
    """
    sim = Simulation.from_scenario(SCENARIOS / "iron_shortage.toml", seed=42)
    world = sim.world

    # Run until day 70, checking board invariants at every step
    for day in range(1, 70):
        sim.step()
        check_board(world, world.contracts)

        # Invariant: across all live non-transport contracts, no NPC is a beneficiary of >1 contract
        live_non_transport = [
            c
            for c in world.contracts.contracts.values()
            if c.live and c.kind is not ContractKind.TRANSPORT
        ]
        beneficiary_pairs = [
            (nid, c.good)
            for c in live_non_transport
            for nid, qty in c.beneficiaries.items()
            if qty > 0
        ]
        assert len(beneficiary_pairs) == len(set(beneficiary_pairs)), (
            f"Day {day}: detected duplicate beneficiary for the same good: {beneficiary_pairs}"
        )


def test_check_board_catches_duplicate_beneficiary():
    """Verify check_board raises ContractInvariantError if two live contracts fund the same NPC."""
    sim = Simulation.from_scenario(SCENARIOS / "baseline.toml", seed=42)
    world = sim.world

    # Run a few days
    sim.step(10)

    # Pick an existing open contract or create a dummy scenario
    live = [
        c
        for c in world.contracts.contracts.values()
        if c.live and c.kind is not ContractKind.TRANSPORT
    ]
    if live:
        c = live[0]
        # Artificially modify a second live contract to fund the same beneficiary
        other_live = [o for o in live if o.id != c.id]
        if other_live:
            target_nid = next(nid for nid, q in c.beneficiaries.items() if q > 0)
            other_c = other_live[0]
            original_bens = dict(other_c.beneficiaries)
            other_c.beneficiaries[target_nid] = 1
            other_c.good = c.good
            try:
                with pytest.raises(
                    ContractInvariantError, match="beneficiary of multiple live contracts"
                ):
                    check_board(world, world.contracts)
            finally:
                other_c.beneficiaries = original_bens
