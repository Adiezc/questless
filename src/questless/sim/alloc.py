# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Deterministic integer apportionment (largest-remainder method).

Leftover units go to the largest fractional remainders. Ties are broken by a seeded random draw
when an ``rng`` is given, otherwise by id. The random tie-break matters: when small totals are
split again and again (two tools of demand across eight smiths, every day), an id tie-break hands
every leftover unit to the same claimants forever, which silently bankrupts the rest.
"""

from __future__ import annotations

import random
from collections.abc import Iterable


def split(
    total: int, weights: Iterable[tuple[str, int]], rng: random.Random | None = None
) -> dict[str, int]:
    """Divide exactly ``total`` units in proportion to ``weights``. Sums to ``total`` unless every
    weight is zero, in which case nothing is handed out."""
    weights = [(k, w) for k, w in weights if w > 0]
    weight_sum = sum(w for _, w in weights)
    if total <= 0 or weight_sum == 0:
        return {k: 0 for k, _ in weights}
    shares = {k: total * w // weight_sum for k, w in weights}
    leftover = total - sum(shares.values())
    if leftover:
        draw = {k: rng.random() for k, _ in weights} if rng else {}
        by_remainder = sorted(
            weights, key=lambda kw: (-(total * kw[1] % weight_sum), draw.get(kw[0], 0.0), kw[0])
        )
        for k, _ in by_remainder[:leftover]:
            shares[k] += 1
    return shares


def allocate(
    total: int, claims: Iterable[tuple[str, int]], rng: random.Random | None = None
) -> dict[str, int]:
    """Fill claims from a limited ``total``: everyone gets their full claim if it fits, otherwise
    a pro-rata share. Never exceeds a claim or the total."""
    claims = [(k, q) for k, q in claims if q > 0]
    if total >= sum(q for _, q in claims):
        return dict(claims)
    return split(total, claims, rng)
