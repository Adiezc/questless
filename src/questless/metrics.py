# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Time series and headline indicators, read from the world's per-tick stats.

Plain dicts of lists so a dashboard, an experiment script or a notebook can use them without
knowing the engine's internals.
"""

from __future__ import annotations

from math import ceil
from statistics import fmean
from typing import TYPE_CHECKING, Any

from questless.sim.ledger import GOODS, Asset

if TYPE_CHECKING:
    from questless.sim.market import MarketReport
    from questless.sim.world import World

# Days 10-14 are "normal": after the warm-up (days 0-9) and before the scenarios' shocks (day 15).
REFERENCE_DAYS = slice(10, 15)


def timeseries(world: World) -> dict[str, Any]:
    stats = world.stats
    goods = [str(g) for g in GOODS]
    return {
        "day": [s.tick for s in stats],
        "price": {g: [round(s.prices[Asset(g)], 2) for s in stats] for g in goods},
        "produced": {g: [s.produced.get(Asset(g), 0) for s in stats] for g in goods},
        "price_index": {g: _index([s.prices[Asset(g)] for s in stats]) for g in goods},
        "produced_index": {g: _index([s.produced.get(Asset(g), 0) for s in stats]) for g in goods},
        "unfilled": {g: [s.market[Asset(g)].unfilled for s in stats] for g in goods},
        "unfilled_pct": {g: [_unfilled_pct(s.market[Asset(g)]) for s in stats] for g in goods},
        "traded": {g: [s.market[Asset(g)].traded for s in stats] for g in goods},
        "hungry": [s.hungry_npcs for s in stats],
        "idle": [s.idle_npcs for s in stats],
        "live_contracts": [s.contracts.live if s.contracts else 0 for s in stats],
        "treasury": {
            gid: [s.guilds[gid].treasury if gid in s.guilds else None for s in stats]
            for gid in sorted(world.guilds)
        },
        "escrowed": {
            gid: [s.guilds[gid].escrowed if gid in s.guilds else None for s in stats]
            for gid in sorted(world.guilds)
        },
        "transport": {
            "capacity": [s.transport.capacity if s.transport else 0 for s in stats],
            "backlog": [s.transport.backlog if s.transport else 0 for s in stats],
        },
        "coin_gini": [round(s.coin_gini, 4) for s in stats],
        "coin_top10_share": [round(s.coin_top10_share, 4) for s in stats],
    }


def gini(values: list[int]) -> float:
    """Gini coefficient of ``values``: 0 when all are equal, (n - 1) / n when one holds everything.

    0 for an empty or all-zero list. Sorted first, so the result doesn't depend on input order.
    """
    ordered = sorted(values)
    n, total = len(ordered), sum(ordered)
    if not total:
        return 0.0
    weighted = sum(rank * v for rank, v in enumerate(ordered, start=1))
    return 2 * weighted / (n * total) - (n + 1) / n


def top_share(values: list[int], fraction: float = 0.1) -> float:
    """Share of the total held by the richest ``fraction`` of holders (at least one); 0 if none."""
    ordered = sorted(values, reverse=True)
    total = sum(ordered)
    if not total:
        return 0.0
    return sum(ordered[: max(1, ceil(len(ordered) * fraction))]) / total


def _unfilled_pct(report: MarketReport) -> float:
    """Unmet demand as a share of demand from buyers who could pay; 0 on a day nobody bid."""
    return round(100 * report.unfilled / report.demand, 1) if report.demand else 0.0


def _index(values: list[float]) -> list[float | None]:
    """``values`` as a percentage of their mean over ``REFERENCE_DAYS``, so 100 means normal.

    All ``None`` until the reference window has passed, or if the good was absent throughout it.
    """
    reference = values[REFERENCE_DAYS]
    full = len(reference) == REFERENCE_DAYS.stop - REFERENCE_DAYS.start
    base = fmean(reference) if full else 0.0
    if not base:
        return [None] * len(values)
    return [round(100 * v / base, 1) for v in values]
