# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""But-for checks: a contract that cites a shock should not have been posted without it."""

import dataclasses

import pytest

from questless.api import Simulation
from questless.audit import NotReplayable, but_for, but_for_all, matches
from questless.bots import ScriptedPlayer
from questless.config import ShockConfig, ShockEffect
from questless.sim.entities import Site
from questless.sim.ledger import Asset
from questless.sim.world import build_world
from tests.conftest import SCENARIOS, mine_collapse, with_shocks


@pytest.fixture(scope="module")
def mine_disaster():
    sim = Simulation.from_scenario(SCENARIOS / "mine_disaster.toml")
    sim.step(60)
    return sim


@pytest.fixture(scope="module")
def with_player():
    """Mine Disaster with a scripted player accepting, sourcing and delivering contracts."""
    sim = Simulation.from_scenario(SCENARIOS / "mine_disaster.toml")
    bot = ScriptedPlayer(sim, "local")
    for _ in range(70):
        bot.act()
        sim.step()
    assert any(a["action"] == "deliver" for a in sim.world.actions)
    return sim


def test_every_shock_cited_in_the_mine_disaster_was_necessary(mine_disaster):
    verdicts = {cid: v for cid, v in but_for_all(mine_disaster.world).items() if v}
    assert verdicts
    for cid, tests in verdicts.items():
        for t in tests:
            assert t.holds and t.posted_without is None, (cid, t)
            assert t.conclusive or t.checked_until == mine_disaster.world.tick - 1, (cid, t)


def test_a_contract_citing_no_shock_has_nothing_to_test(baseline):
    world = build_world(baseline)
    world.step(160)  # long enough for the baseline to post contracts of its own
    assert world.contracts.contracts, "the baseline needs to post something for this test"
    assert all(v == [] for v in but_for_all(world).values())


def test_overdetermined_contracts_fail_each_single_test_but_pass_the_joint_one(baseline):
    """Two shocks, each enough on its own: neither was necessary, both together were."""
    flood = ShockConfig("Flooded shaft", ShockEffect.SITE_OUTPUT, 20, 30, 0.1, Site.MINE)
    world = build_world(with_shocks(baseline, mine_collapse(factor=0.1), flood))
    world.step(60)
    both = [v for v in but_for_all(world).values() if len(v) == 3]
    overdetermined = [v for v in both if not v[0].holds and not v[1].holds]
    assert overdetermined, both
    for v in overdetermined:
        singles, joint = v[:2], v[2]
        assert joint.shocks == ("Mine collapse", "Flooded shaft")
        assert joint.holds
        assert all(s.posted_without is not None for s in singles)


def test_but_for_all_agrees_with_one_contract_at_a_time_even_with_a_player(with_player):
    world = with_player.world
    every = but_for_all(world)
    cited = [c for c in world.contracts.contracts.values() if every[c.id]]
    assert cited
    for c in cited[:6]:
        assert but_for(world, c) == every[c.id], c.id
        assert with_player.but_for(c.id) == every[c.id], c.id


def test_player_actions_follow_their_contract_into_the_counterfactual(with_player):
    """Contract ids shift once a shock is removed, so actions are matched by need and posting
    day. Actions with no counterpart are dropped, and any divergence makes the verdict
    inconclusive rather than quietly dropping the player."""
    world = with_player.world
    verdicts = [t for v in but_for_all(world).values() for t in v]
    assert any(t.dropped_actions for t in verdicts)
    for t in verdicts:
        fits = t.checked_until < world.tick - 1
        assert t.conclusive == (fits and not t.dropped_actions and not t.rejected_actions), t


def test_an_action_lands_on_the_counterpart_for_the_same_need(with_player):
    from questless.audit import _counterfactual, _counterpart

    world = with_player.world
    twin, _, _ = _counterfactual(world, frozenset({0}), world.tick)
    for cid, real in world.contracts.contracts.items():
        match = _counterpart(world, twin, cid)
        if match is not None:
            rebuilt = twin.contracts.contracts[match]
            assert (rebuilt.dedup_key, rebuilt.created_tick) == (real.dedup_key, real.created_tick)


def test_a_window_cut_short_by_the_end_of_the_run_is_inconclusive(mine_disaster):
    world = mine_disaster.world
    verdicts = but_for_all(world)
    contract = max(
        (c for c in world.contracts.contracts.values() if verdicts[c.id]),
        key=lambda c: c.created_tick,
    )
    for verdict in but_for(world, contract, window=1000):
        assert verdict.checked_until == world.tick - 1
        assert not verdict.conclusive


def test_window_edges(mine_disaster):
    """A matching posting exactly ``window`` days away counts; one day further does not, unless
    it was posted earlier and was still live (it would have blocked the original as a duplicate)."""
    original = next(iter(mine_disaster.world.contracts.contracts.values()))
    t = original.created_tick
    later = dataclasses.replace(original, id="X", created_tick=t + 7)
    assert matches(later, original, window=7)
    assert not matches(dataclasses.replace(later, created_tick=t + 8), original, window=7)
    earlier = dataclasses.replace(original, id="X", created_tick=t - 9, deadline_tick=t + 1)
    assert matches(earlier, original, window=7)  # still live on day t
    assert not matches(dataclasses.replace(earlier, closed_tick=t), original, window=7)
    other_good = dataclasses.replace(later, good=Asset.WEAPONS, dedup_key=("x", "y", "weapons"))
    assert not matches(other_good, original, window=7)


def test_a_tampered_world_gets_no_verdicts(baseline):
    world = build_world(with_shocks(baseline, mine_collapse()))
    world.step(50)
    world.ledger.transfer("town", "outside", Asset.COIN, 1, tick=world.tick, reason="test")
    contract = next(iter(world.contracts.contracts.values()))
    with pytest.raises(NotReplayable):
        but_for(world, contract)
    with pytest.raises(NotReplayable):
        but_for_all(world)


def test_the_counterfactual_leaves_the_real_world_alone(mine_disaster):
    world = mine_disaster.world
    before, shocks = world.state_hash(), world.config.shocks
    for c in world.contracts.contracts.values():
        but_for(world, c)
        break
    assert world.state_hash() == before
    assert world.config.shocks == shocks and len(world.modifiers.shocks) == len(shocks)
    assert dataclasses.is_dataclass(world.config)


# --- aftermath attribution ------------------------------------------------------------------


@pytest.mark.parametrize("factor", [0.95, 0.9])
@pytest.mark.parametrize("site", [Site.MINE, Site.FARMS])
def test_a_mild_shock_is_never_blamed_for_the_aftermath(baseline, factor, site):
    """Placebo: a shock too mild to count as a drop can't be cited once it has ended."""
    mild = ShockConfig("Mild", ShockEffect.SITE_OUTPUT, 15, 25, factor, site)
    world = build_world(with_shocks(baseline, mild))
    world.step(200)
    chains = [c.provenance.chain for c in world.contracts.contracts.values()]
    assert not any(e.kind == "shock_aftermath" for chain in chains for e in chain)


@pytest.fixture(scope="module")
def mine_disaster_aftermath():
    sim = Simulation.from_scenario(SCENARIOS / "mine_disaster.toml")
    sim.step(120)  # the disaster runs to day 55; its aftermath comes after
    return sim


def test_the_mine_disaster_aftermath_is_attributed_and_checks_out(mine_disaster_aftermath):
    """Weeks after the disaster ends, ore output still hasn't recovered (broke miners can't buy
    tools), so later contracts cite the disaster through a measured aftermath step. Most of them
    pass the but-for test; the few that don't are needs the baseline would have posted anyway."""
    sim = mine_disaster_aftermath
    world = sim.world
    late = [
        c
        for c in world.contracts.contracts.values()
        if any(e.kind == "shock_aftermath" for e in c.provenance.chain)
    ]
    assert late
    shock = world.modifiers.shocks[0]
    for c in late:
        after = next(e for e in c.provenance.chain if e.kind == "shock_aftermath")
        assert c.created_tick >= shock.end + 7
        assert after.value < after.threshold < after.baseline
        assert c.provenance.chain[after.caused_by[0]].kind == "shock"
    assert all(not p for p in sim.audit().values())
    verdicts = but_for_all(world)
    conclusive = [v[0] for c in late if (v := verdicts[c.id]) and v[0].conclusive]
    assert conclusive and sum(v.holds for v in conclusive) >= 0.85 * len(conclusive)
