# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""#72: below its reserve target the town raises the levy until it recovers, so a long run no
longer drains it to zero and leaves guards unpaid."""

import dataclasses

from questless.config import load_scenario
from questless.sim.entities import OUTSIDE, TOWN, Profession
from questless.sim.ledger import Asset
from questless.sim.world import build_world
from tests.conftest import SCENARIOS


def _town(baseline, **kw):
    return dataclasses.replace(baseline, town=dataclasses.replace(baseline.town, **kw))


def _upkeep_today(cfg, town_coin):
    world = build_world(cfg)
    world.ledger.transfer(
        TOWN,
        OUTSIDE,
        Asset.COIN,
        world.ledger.balance(TOWN, Asset.COIN) - town_coin,
        tick=0,
        reason="test",
    )
    total = world.ledger.total(Asset.COIN)
    world.step()
    world.check_invariants()
    assert world.ledger.total(Asset.COIN) == total  # the top-up moves coin, never makes it
    return world.stats[-1].upkeep


def test_surcharge_applies_only_below_the_reserve(baseline):
    on, off = _town(baseline, reserve_days=10, reserve_rate=0.05), _town(baseline, reserve_days=0)
    target = 10 * baseline.town.guard_wage * baseline.professions[Profession.GUARD].count
    assert _upkeep_today(on, target - 1) > _upkeep_today(off, target - 1)
    assert _upkeep_today(on, target + 1000) == _upkeep_today(off, target + 1000)


def test_long_baseline_run_keeps_guards_paid(baseline):
    """Seed 3 drained the town to 0 by day 632 and left guards unpaid on 341 days (#72)."""
    seed3 = dataclasses.replace(baseline, seed=3)
    guards = baseline.professions[Profession.GUARD].count
    target = baseline.town.reserve_days * baseline.town.guard_wage * guards
    fixed, drained = build_world(seed3), build_world(_town(seed3, reserve_days=0))
    drained.step(1000)
    lowest = None
    for day in range(1000):
        fixed.step()
        if day >= 365:
            coin = fixed.ledger.balance(TOWN, Asset.COIN)
            lowest = coin if lowest is None else min(lowest, coin)
    assert sum(1 for s in drained.stats if s.wages_unpaid) > 0  # the bug, without the reserve
    assert all(s.wages_unpaid == 0 for s in fixed.stats)
    assert lowest >= 0.9 * target
    fixed.check_invariants()


def test_reserve_softens_the_legitimacy_spiral():
    """The spiral scenario turns the reserve off to show the trap (legitimacy near 0.5 by day 90).
    With it on, a town starting on 300 coin still can't pay every guard, but pays enough of them
    that legitimacy holds near 0.8 and NPCs keep paying the levy."""
    cfg = load_scenario(SCENARIOS / "legitimacy_spiral.toml")
    for seed in range(1, 4):
        trapped = build_world(dataclasses.replace(cfg, seed=seed))
        helped = build_world(_town(dataclasses.replace(cfg, seed=seed), reserve_days=10))
        trapped.step(90)
        helped.step(90)
        assert trapped.legitimacy < 0.6 < 0.75 < helped.legitimacy
        unpaid = [sum(s.wages_unpaid for s in w.stats) for w in (trapped, helped)]
        assert unpaid[1] < unpaid[0]
        helped.check_invariants()
