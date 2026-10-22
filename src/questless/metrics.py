# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Time series and headline indicators, read from the world's per-tick stats.

Plain dicts of lists so a dashboard, an experiment script or a notebook can use them without
knowing the engine's internals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from questless.sim.ledger import GOODS, Asset

if TYPE_CHECKING:
    from questless.sim.world import World


def timeseries(world: World) -> dict[str, Any]:
    stats = world.stats
    goods = [str(g) for g in GOODS]
    return {
        "day": [s.tick for s in stats],
        "price": {g: [round(s.prices[Asset(g)], 2) for s in stats] for g in goods},
        "produced": {g: [s.produced.get(Asset(g), 0) for s in stats] for g in goods},
        "unfilled": {g: [s.market[Asset(g)].unfilled for s in stats] for g in goods},
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
    }
