# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M1 acceptance: 100 NPCs from a seed; identical totals and state across builds."""

import dataclasses

from questless.sim.entities import ESCROW, OUTSIDE, PLAYER, TOWN, Profession
from questless.sim.ledger import Asset
from questless.sim.world import build_world


def test_builds_100_npcs_with_expected_professions(baseline):
    world = build_world(baseline)
    assert len(world.npcs) == 100
    counts = {p: len(world.npcs_by_profession(p)) for p in Profession}
    assert counts == {p: baseline.professions[p].count for p in Profession}
    assert len({n.name for n in world.npcs.values()}) == 100  # names are unique


def test_same_seed_gives_identical_world(baseline):
    a, b = build_world(baseline), build_world(baseline)
    assert a.ledger.totals() == b.ledger.totals()
    assert a.state_hash() == b.state_hash()
    assert [n.traits for n in a.npcs_in_order()] == [n.traits for n in b.npcs_in_order()]


def test_different_seed_gives_different_world(baseline):
    other = build_world(dataclasses.replace(baseline, seed=baseline.seed + 1))
    assert other.state_hash() != build_world(baseline).state_hash()


def test_genesis_coin_is_fully_accounted_for(baseline):
    world = build_world(baseline)
    npc_coin = sum(world.ledger.balance(n.account, Asset.COIN) for n in world.npcs.values())
    guild_coin = sum(world.ledger.balance(g.account, Asset.COIN) for g in world.guilds.values())
    assert guild_coin == sum(g.treasury for g in baseline.guilds.values())
    assert world.ledger.balance(TOWN, Asset.COIN) == baseline.town.treasury
    assert world.ledger.balance(PLAYER, Asset.COIN) == baseline.player_wallet
    assert world.ledger.balance(ESCROW, Asset.COIN) == 0
    assert world.ledger.balance(OUTSIDE, Asset.COIN) == 0
    assert world.ledger.total(Asset.COIN) == (
        npc_coin + guild_coin + baseline.town.treasury + baseline.player_wallet
    )
    world.check_invariants()


def test_guild_membership_matches_config(baseline):
    world = build_world(baseline)
    for gid, guild in world.guilds.items():
        professions = baseline.guilds[gid].professions
        assert guild.members == sorted(
            n.id for n in world.npcs.values() if n.profession in professions
        )
    guards = world.npcs_by_profession(Profession.GUARD)
    assert all(g.guild_id is None for g in guards)


def test_guilds_disabled_opens_no_guild_accounts(baseline):
    world = build_world(dataclasses.replace(baseline, guilds_enabled=False))
    assert world.guilds == {}
    assert not [a for a in world.ledger.accounts() if a.startswith("guild:")]
    assert all(n.guild_id is None for n in world.npcs.values())


def test_traits_respect_configured_ranges(baseline):
    t = baseline.traits
    for npc in build_world(baseline).npcs.values():
        assert t.skill[0] <= npc.traits.skill <= t.skill[1]
        assert t.stock_days[0] <= npc.traits.stock_days <= t.stock_days[1]
        assert t.patience[0] <= npc.traits.patience <= t.patience[1]
