# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Legitimacy (M48): the town's authority as a stock that can run down.

Legitimacy is one number in [0, 1]. Each day, after guard wages, it moves towards
``1 - pressure``, where pressure is the larger of the share of today's wages left unpaid and the
share of NPCs hungry over the last ``hunger_window`` days. It falls fast (``fall_rate``) and
recovers slowly (``recover_rate``). The next day's levy uses it: each NPC pays with probability
``compliance``, and evaded coin simply stays in the NPC's wallet, so the ledger never changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from questless.sim.world import TickStats, World


def pressure(world: World, stats: TickStats) -> float:
    """Pressure on the town today: unpaid wage share or recent hunger share, whichever is worse."""
    owed = stats.wages_paid + stats.wages_unpaid
    unpaid = stats.wages_unpaid / owed if owed else 0.0
    window = world.config.legitimacy.hunger_window
    recent = [s.hungry_npcs for s in world.stats[-(window - 1) :]] if window > 1 else []
    hungry = (sum(recent) + stats.hungry_npcs) / (len(recent) + 1) / max(len(world.npcs), 1)
    return min(max(unpaid, hungry), 1.0)


def update(world: World, stats: TickStats) -> None:
    """Move legitimacy towards ``1 - pressure`` and record it on today's stats."""
    cfg = world.config.legitimacy
    target = 1.0 - pressure(world, stats)
    rate = cfg.fall_rate if target < world.legitimacy else cfg.recover_rate
    world.legitimacy = min(max(world.legitimacy + rate * (target - world.legitimacy), 0.0), 1.0)
    stats.legitimacy = world.legitimacy


def compliance(world: World) -> float:
    """The chance an NPC pays today's levy: ``min_compliance`` at legitimacy 0, 1 at full."""
    floor = world.config.legitimacy.min_compliance
    return floor + (1.0 - floor) * world.legitimacy
