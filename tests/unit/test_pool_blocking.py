# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Tests for pool contracts and member contract generation (M13.8)."""

from questless.contracts.model import ContractKind
from questless.sim.world import build_world
from tests.conftest import drought, mine_collapse, with_shocks


def test_no_contract_has_zero_qty_beneficiary(baseline):
    """Contracts never store 0-quantity beneficiaries after allocation."""
    cfg = with_shocks(
        baseline,
        mine_collapse(start=10, duration=60, factor=0.1),
        drought(start=20, duration=50, factor=0.2),
    )
    world = build_world(cfg)
    for _ in range(60):
        world.step()
        for c in world.contracts.contracts.values():
            assert not any(qty <= 0 for qty in c.beneficiaries.values()), (
                f"{c.id} contains non-positive beneficiary quantity: {c.beneficiaries}"
            )


def test_member_omitted_from_pool_can_post_individual_contract(baseline):
    """A member allocated 0 units in a pool can post their own procurement contract."""
    cfg = with_shocks(
        baseline,
        mine_collapse(start=10, duration=60, factor=0.1),
        drought(start=20, duration=50, factor=0.2),
    )
    world = build_world(cfg)
    coexisting = False
    for _ in range(35):
        world.step()
        live = world.contracts.live()
        pools = [c for c in live if c.kind is ContractKind.GUILD_SUPPLY]
        inds = [c for c in live if c.kind is ContractKind.PROCUREMENT]
        for pool in pools:
            for ind in inds:
                guild_name = pool.funder.removeprefix("guild:")
                if pool.good == ind.good and ind.requester in world.guilds[guild_name].members:
                    assert pool.beneficiaries.get(ind.requester, 0) == 0
                    assert ind.requester in ind.beneficiaries
                    assert ind.beneficiaries[ind.requester] > 0
                    coexisting = True
                    break
            if coexisting:
                break
        if coexisting:
            break

    assert coexisting, (
        "Expected an omitted member to post an individual contract alongside a live pool"
    )
