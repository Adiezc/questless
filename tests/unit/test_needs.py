# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
import pytest

from questless.contracts.needs import NeedTracker
from questless.sim.entities import Profession
from questless.sim.ledger import Asset
from questless.sim.world import build_world


@pytest.fixture
def world(baseline):
    w = build_world(baseline)
    w.step()
    return w


def _mark(world, npc, good, unmet=0, unfilled=0, unaffordable=0):
    rec = npc.history[-1]
    rec.unmet.clear(), rec.unfilled.clear(), rec.unaffordable.clear()
    for field, qty in (("unmet", unmet), ("unfilled", unfilled), ("unaffordable", unaffordable)):
        if qty:
            getattr(rec, field)[good] = qty


def test_scarcity_needs_both_unmet_and_unfilled(world):
    tracker = NeedTracker()
    smith = world.npcs_by_profession(Profession.BLACKSMITH)[0]
    _mark(world, smith, Asset.IRON_ORE, unmet=4)  # short, but market not asked: not scarcity
    tracker.update(world)
    assert tracker.get(smith.id, Asset.IRON_ORE) is None
    _mark(world, smith, Asset.IRON_ORE, unmet=4, unfilled=4)
    tracker.update(world)
    assert tracker.get(smith.id, Asset.IRON_ORE).days == 1


def test_poverty_is_not_scarcity(world):
    tracker = NeedTracker()
    guard = world.npcs_by_profession(Profession.GUARD)[0]
    _mark(world, guard, Asset.FOOD, unmet=1, unaffordable=3)
    tracker.update(world)
    assert tracker.get(guard.id, Asset.FOOD) is None
    assert tracker.poverty_days[Asset.FOOD] >= 1


def test_need_becomes_persistent_after_patience(world):
    tracker = NeedTracker()
    smith = world.npcs_by_profession(Profession.BLACKSMITH)[0]
    for day in range(smith.traits.patience):
        assert all(s.subject != smith.id for s in tracker.persistent(world)), day
        _mark(world, smith, Asset.IRON_ORE, unmet=4, unfilled=4)
        tracker.update(world)
    assert any(s.subject == smith.id for s in tracker.persistent(world))


def test_streak_survives_a_one_day_gap_but_not_two(world):
    tracker = NeedTracker()
    smith = world.npcs_by_profession(Profession.BLACKSMITH)[0]
    for marks in [(4, 4), (4, 4), (0, 0), (4, 4)]:
        _mark(world, smith, Asset.IRON_ORE, *marks)
        tracker.update(world)
    assert tracker.get(smith.id, Asset.IRON_ORE).days == 3
    for marks in [(0, 0), (0, 0), (4, 4)]:
        _mark(world, smith, Asset.IRON_ORE, *marks)
        tracker.update(world)
    assert tracker.get(smith.id, Asset.IRON_ORE).days == 1  # new streak
