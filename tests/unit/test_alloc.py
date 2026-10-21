# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
import random
from collections import Counter

import pytest

from questless.sim.alloc import allocate, split


def test_full_claims_when_total_suffices():
    assert allocate(10, [("a", 3), ("b", 4)]) == {"a": 3, "b": 4}


@pytest.mark.parametrize("total", [0, 1, 5, 9, 13])
def test_allocation_never_exceeds_total_or_claims(total):
    claims = [("a", 7), ("b", 5), ("c", 2)]
    out = allocate(total, claims)
    assert sum(out.values()) == min(total, 14)
    assert all(out[k] <= q for k, q in claims)


def test_split_is_exact_and_proportional():
    out = split(100, [("a", 1), ("b", 3)])
    assert out == {"a": 25, "b": 75}
    assert sum(split(7, [("a", 1), ("b", 1), ("c", 1)]).values()) == 7


def test_seeded_tie_breaks_are_deterministic():
    claims = [(f"n{i}", 3) for i in range(8)]
    assert allocate(2, claims, random.Random(1)) == allocate(2, claims, random.Random(1))


def test_repeated_small_splits_are_fair_over_time():
    """Regression: an id tie-break gave every leftover unit to the same claimants forever."""
    rng = random.Random(7)
    claims = [(f"n{i}", 3) for i in range(8)]
    wins: Counter[str] = Counter()
    for _ in range(4000):
        wins.update({k: v for k, v in allocate(2, claims, rng).items() if v})
    assert min(wins.values()) > 0.8 * max(wins.values())
