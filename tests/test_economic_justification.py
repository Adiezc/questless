# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""The core claims: contracts are caused by the simulation, funded, and kept in check.

T1  an iron shortage produces an iron procurement contract with a causal record
T3  nobody can post a contract they cannot fund
T5  one live contract per need, however long the shortage lasts
T6  contracts do not flap between created and cancelled
T10 caps hold under extreme combined shocks
(T2 completion effects arrives with player actions in M7; T4 counterfactual is below.)
"""

import dataclasses
from collections import Counter

from questless.contracts.engine import Candidate, ContractTickReport
from questless.contracts.model import ContractKind, Status
from questless.sim.entities import ESCROW, OUTSIDE, Profession
from questless.sim.ledger import Asset
from questless.sim.world import build_world
from tests.conftest import bandits, drought, mine_collapse, with_shocks


def _contracts(world, good=None, kinds=None):
    return [
        c
        for c in world.contracts.contracts.values()
        if (good is None or c.good is good) and (kinds is None or c.kind in kinds)
    ]


def test_t1_iron_shortage_produces_a_funded_iron_contract_with_provenance(baseline):
    world = build_world(with_shocks(baseline, mine_collapse(start=20)))
    world.step(40)
    iron = _contracts(world, Asset.IRON_ORE)
    assert iron, "no iron contract after a mine collapse"
    first = min(iron, key=lambda c: c.created_tick)
    assert 20 < first.created_tick <= 35  # caused by the shock, within ~2 weeks of it
    smiths = {n.id for n in world.npcs_by_profession(Profession.BLACKSMITH)}
    assert first.funder in smiths | {"guild:blacksmiths"}
    assert set(first.beneficiaries) <= smiths
    kinds = [e.kind for e in first.provenance.chain]
    assert "unfilled_demand" in kinds and kinds[-1] == "funding_decision"
    unfilled = next(e for e in first.provenance.chain if e.kind == "unfilled_demand")
    assert unfilled.subject == "market:iron_ore"
    assert unfilled.value == world.stats[first.created_tick].market[Asset.IRON_ORE].unfilled > 0


def test_t4_counterfactual_no_shock_no_iron_guild_contract(baseline):
    world = build_world(baseline)
    world.step(40)
    assert not _contracts(world, Asset.IRON_ORE, {ContractKind.GUILD_SUPPLY})


def test_baseline_year_posts_few_contracts(baseline):
    world = build_world(baseline)
    world.step(365)
    assert len(world.contracts.contracts) <= 12


def test_t3_guild_without_funds_cannot_post_and_escrow_is_untouched(baseline):
    world = build_world(with_shocks(baseline, mine_collapse(start=20)))
    world.step(31)  # needs are persistent; the first contract would appear on day 32
    guild = world.guilds["blacksmiths"]
    treasury = world.ledger.balance(guild.account, Asset.COIN)
    world.ledger.transfer(guild.account, OUTSIDE, Asset.COIN, treasury, tick=31, reason="test")
    world.step(5)
    assert not [c for c in world.contracts.contracts.values() if c.funder == guild.account]


def test_t3_unfunded_candidate_is_rejected_and_counted(baseline):
    world = build_world(baseline)
    world.step()
    smith = world.npcs_by_profession(Profession.BLACKSMITH)[0]
    guild = world.guilds["blacksmiths"]
    for account in (smith.account, guild.account):
        coin = world.ledger.balance(account, Asset.COIN)
        world.ledger.transfer(account, OUTSIDE, Asset.COIN, coin, tick=1, reason="test")
    world.needs.update(world)
    cand = Candidate(
        ContractKind.PROCUREMENT,
        smith.id,
        Asset.IRON_ORE,
        {smith.id: 10},
        needs=[_fake_need(world, smith.id)],
        guild_id="blacksmiths",
    )
    escrow = world.ledger.balance(ESCROW, Asset.COIN)
    report = ContractTickReport()
    assert world.contracts._try_post(world, cand, report) is None
    assert report.suppressed["unfunded"] == 1
    assert world.ledger.balance(ESCROW, Asset.COIN) == escrow


def test_t5_one_live_contract_per_need(baseline):
    world = build_world(with_shocks(baseline, mine_collapse(start=10, duration=60, factor=0.1)))
    suppressed: Counter[str] = Counter()
    for _ in range(70):
        world.step()
        keys = [c.dedup_key for c in world.contracts.live()]
        assert len(keys) == len(set(keys))
        suppressed.update(world.stats[-1].contracts.suppressed)
    assert suppressed["duplicate"] + suppressed["covered_by_pool"] > 0


def test_t6_contracts_do_not_flap(baseline):
    """After a contract for a need closes unfulfilled, the next one for the same need waits out
    the cooldown."""
    world = build_world(
        with_shocks(baseline, mine_collapse(), drought(start=40), bandits(start=60))
    )
    world.step(120)
    cooldown = baseline.contracts.cooldown_days
    by_key: dict[tuple, list] = {}
    for c in sorted(world.contracts.contracts.values(), key=lambda c: c.created_tick):
        by_key.setdefault(c.dedup_key, []).append(c)
    repeats = 0
    for contracts in by_key.values():
        for prev, nxt in zip(contracts, contracts[1:], strict=False):
            assert prev.status in (Status.EXPIRED, Status.CANCELLED)
            assert nxt.created_tick >= prev.closed_tick + cooldown
            repeats += 1
    assert repeats > 0  # the scenario does exercise re-posting


def test_t10_caps_hold_under_extreme_shocks(baseline):
    shocks = (
        mine_collapse(start=5, duration=80, factor=0.0),
        drought(start=5, duration=80, factor=0.1),
        bandits(start=5, duration=80, factor=0.1),
    )
    world = build_world(with_shocks(baseline, *shocks))
    cfg = baseline.contracts
    for _ in range(90):
        world.step()  # board invariants (escrow, caps, duplicates) are checked every tick
        assert len(world.contracts.live()) <= cfg.max_open
        assert len(world.stats[-1].contracts.created) <= cfg.max_new_per_tick
    assert any(s.contracts.suppressed["cap_reached"] for s in world.stats)


def test_guilds_disabled_means_no_guild_contracts(baseline):
    cfg = with_shocks(dataclasses.replace(baseline, guilds_enabled=False), mine_collapse())
    world = build_world(cfg)
    world.step(60)
    assert not [c for c in world.contracts.contracts.values() if c.funder.startswith("guild:")]
    assert _contracts(world, Asset.IRON_ORE)  # smiths still ask for help themselves


def _fake_need(world, npc_id):
    from questless.contracts.needs import NeedState

    return NeedState(npc_id, Asset.IRON_ORE, since=world.tick, days=5, unmet=4, unfilled=4)
