# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Regression guard for the baseline economy: a full year without shocks stays stable.

Thresholds are deliberately loose; milestone M9 (calibration) tightens them.
"""

import dataclasses
import statistics

import pytest

from questless.sim.ledger import GOODS, Asset
from questless.sim.world import build_world


def test_baseline_year_is_stable(baseline):
    world = build_world(baseline)
    world.step(365)
    late = world.stats[100:]
    assert statistics.mean(s.hungry_npcs for s in late) < 10
    assert sum(1 for s in world.stats if s.wages_unpaid) == 0
    for good in GOODS:
        prices = [s.prices[good] for s in late]
        assert statistics.pstdev(prices) / statistics.mean(prices) < 0.6, good
    world.check_invariants()


@pytest.mark.parametrize("seed", [42, 7])
def test_long_baseline_keeps_paying_guards(baseline, seed):
    """#48: over 2,000 days guild treasuries don't hoard the town's coin."""
    world = build_world(dataclasses.replace(baseline, seed=seed))
    total = world.ledger.total(Asset.COIN)
    world.step(2000)
    assert sum(1 for s in world.stats if s.wages_unpaid) == 0
    assert max(r.treasury for s in world.stats for r in s.guilds.values()) <= 0.25 * total
    world.check_invariants()
