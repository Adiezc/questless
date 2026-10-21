# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M2 acceptance: the tick loop runs, conserves goods and coin, and shocks scale output."""

import dataclasses

import pytest

from questless.config import ShockConfig, ShockEffect
from questless.sim.entities import Profession, Site
from questless.sim.ledger import Asset
from questless.sim.world import build_world


def _with_shock(cfg, factor, start=0, duration=100, site=Site.MINE):
    shock = ShockConfig("Mine collapse", ShockEffect.SITE_OUTPUT, start, duration, factor, site)
    return dataclasses.replace(cfg, shocks=(shock,))


def _effective_ore(world) -> float:
    """Ore produced plus fractional carry still owed: removes integer rounding noise."""
    miners = world.npcs_by_profession(Profession.MINER)
    produced = sum(
        s.produced_by_site.get(Site.MINE, {}).get(Asset.IRON_ORE, 0) for s in world.stats
    )
    return produced + sum(m.carry.get("iron_ore", 0.0) for m in miners)


def test_thirty_ticks_conserve_everything_every_tick(baseline):
    world = build_world(baseline)
    for _ in range(30):
        world.step()  # check_every_tick raises ConservationError on any leak
    assert world.tick == 30
    assert len(world.stats) == 30
    flows = world.ledger.flows()
    for asset in Asset:
        expected = (
            flows["genesis"].get(asset, 0)
            + flows["produced"].get(asset, 0)
            - flows["consumed"].get(asset, 0)
        )
        assert world.ledger.total(asset) == expected
    assert world.ledger.total(Asset.COIN) == flows["genesis"][Asset.COIN]


def test_mine_shock_scales_ore_output_by_its_factor(baseline):
    """Same day, same prices: output scales exactly by the shock factor. (Over longer runs the
    market responds, since scarce ore costs more and miners work harder, which is intended.)"""
    normal = build_world(baseline)
    shocked = build_world(_with_shock(baseline, factor=0.3))
    normal.step()
    shocked.step()
    ratio = _effective_ore(shocked) / _effective_ore(normal)
    assert ratio == pytest.approx(0.3, rel=0.05)


def test_mine_shock_does_not_touch_other_sites(baseline):
    normal = build_world(baseline)
    shocked = build_world(_with_shock(baseline, factor=0.3))
    normal.step(10)
    shocked.step(10)
    food = [
        sum(s.produced_by_site[Site.FARMS][Asset.FOOD] for s in w.stats) for w in (normal, shocked)
    ]
    assert food[0] == food[1]


def test_shock_only_applies_inside_its_window(baseline):
    world = build_world(_with_shock(baseline, factor=0.0, start=5, duration=3))
    world.step(10)
    ore = [s.produced_by_site[Site.MINE].get(Asset.IRON_ORE, 0) for s in world.stats]
    assert all(q == 0 for q in ore[5:8])
    assert all(q > 0 for q in ore[:5])


def test_runs_are_deterministic(baseline):
    a, b = build_world(baseline), build_world(baseline)
    a.step(30)
    b.step(30)
    assert a.state_hash() == b.state_hash()


def test_state_hash_changes_as_the_world_evolves(baseline):
    world = build_world(baseline)
    before = world.state_hash()
    world.step()
    assert world.state_hash() != before
