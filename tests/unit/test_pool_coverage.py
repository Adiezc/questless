# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""#46: a pool covers only the members it gives units to. Members a partly funded pool leaves out,
or who ran short after it was posted, can still post their own contracts."""

import dataclasses

from questless.config import load_scenario
from questless.contracts.model import ContractKind
from questless.sim.world import build_world
from tests.conftest import SCENARIOS

POOLS = (ContractKind.GUILD_SUPPLY, ContractKind.TOWN_SUPPLY)


def _run(scenario, days, seed=None):
    cfg = load_scenario(SCENARIOS / f"{scenario}.toml")
    world = build_world(dataclasses.replace(cfg, seed=seed) if seed is not None else cfg)
    for _ in range(days):
        world.step()
        yield world


def test_no_contract_lists_a_member_it_gives_nothing():
    for scenario in ("iron_shortage", "mine_disaster"):
        *_, world = _run(scenario, 120)
        for c in world.contracts.contracts.values():
            assert all(qty > 0 for qty in c.beneficiaries.values()), (scenario, c.id)
        world.check_invariants()


def test_member_left_out_of_a_live_pool_posts_their_own_contract():
    """Iron Shortage, day 34: the blacksmiths' iron ore pool (C-0001) is live and npc_056, a smith
    it leaves out, posts their own contract (C-0002). Before #46 that need was suppressed."""
    seen = []
    for world in _run("iron_shortage", 40):
        live = world.contracts.live()
        for pool in (c for c in live if c.kind in POOLS):
            for c in live:
                if (
                    c.kind is ContractKind.PROCUREMENT
                    and c.good == pool.good
                    and pool.requester == f"guild:{world.npcs[c.requester].guild_id}"
                    and c.requester not in pool.beneficiaries
                ):
                    seen.append((c.id, pool.id))
        world.check_invariants()  # still no member funded twice for one good
    assert seen


def test_guild_can_fund_its_pool_and_a_left_out_member_at_once():
    """The guild may now fund a member's own contract while its pool for the same good is live.
    Each is escrowed separately and no member is funded twice for one good."""
    both = 0
    for world in _run("iron_shortage", 120, seed=3):
        live = world.contracts.live()
        for pool in (c for c in live if c.kind is ContractKind.GUILD_SUPPLY):
            for c in live:
                if (
                    c.kind is ContractKind.PROCUREMENT
                    and c.good == pool.good
                    and c.funder == pool.funder
                ):
                    assert c.requester not in pool.beneficiaries
                    both += 1
        world.check_invariants()  # escrow matches live rewards; no double funding
    assert both
