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


def ration(
    total: int, claims: Iterable[tuple[str, int]], rng: random.Random | None = None
) -> dict[str, int]:
    """Share a scarce ``total`` *equally* across claimants (water-filling): small claims are met
    in full, everyone else gets the same amount. Leftover single units go by seeded draw.

    Used for buyers in a shortage: pro-rata by bid size would hand most of the goods to whoever
    can afford the biggest bid, which compounds wealth into monopoly."""
    claims = sorted(((k, q) for k, q in claims if q > 0), key=lambda kq: (kq[1], kq[0]))
    if total >= sum(q for _, q in claims):
        return dict(claims)
    out: dict[str, int] = {}
    remaining, left = total, len(claims)
    for i, (k, q) in enumerate(claims):
        level = remaining // left
        if q <= level:
            out[k] = q
            remaining -= q
            left -= 1
            continue
        # Every remaining claim exceeds the level: give each the level, spread the rest.
        rest = claims[i:]
        for k2, _ in rest:
            out[k2] = level
        extra = remaining - level * len(rest)
        order = sorted(rest, key=lambda kq: ((rng.random() if rng else 0.0), kq[0]))
        for k2, _ in order[:extra]:
            out[k2] += 1
        break
    return out
