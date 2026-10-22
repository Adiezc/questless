# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Impact scoring for agent evaluation (M24.1).

Computes counterfactual impact: compares a run against a deterministic no-player
counterfactual run with the exact same scenario and seed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from questless.sim.world import World

_BASELINE_CACHE: dict[tuple[str, int, int], dict[str, float]] = {}


def compute_baseline_stats(scenario_path: str, seed: int, days: int) -> dict[str, float]:
    """Compute and cache the unperturbed counterfactual run stats."""
    cache_key = (scenario_path, seed, days)
    if cache_key in _BASELINE_CACHE:
        return _BASELINE_CACHE[cache_key]

    from questless.api import Simulation

    sim = Simulation.from_scenario(scenario_path, seed=seed)
    sim.step(days)
    world = sim.world

    hungry_days = sum(s.hungry_npcs for s in world.stats)
    shortage_days = sum(sum(m.unfilled for m in s.market.values()) for s in world.stats)
    producer_sales = sum(sum(m.traded for m in s.market.values()) for s in world.stats)

    res = {
        "hungry_days": float(hungry_days),
        "shortage_days": float(shortage_days),
        "producer_sales": float(producer_sales),
    }
    _BASELINE_CACHE[cache_key] = res
    return res


def score(world: World, scenario_path: str, seed: int) -> float:
    """Calculate the agent's net positive impact score compared to baseline.

    Positive score = reduced hunger, reduced shortages, boosted local economy.
    """
    days = len(world.stats)
    if days == 0:
        return 0.0

    base = compute_baseline_stats(scenario_path, seed, days)

    agent_hungry = sum(s.hungry_npcs for s in world.stats)
    agent_shortage = sum(sum(m.unfilled for m in s.market.values()) for s in world.stats)
    agent_sales = sum(sum(m.traded for m in s.market.values()) for s in world.stats)

    # Saved hungry NPC days (+10 pts each)
    hunger_saved = (base["hungry_days"] - agent_hungry) * 10.0
    # Shortages averted (+5 pts each)
    shortages_averted = (base["shortage_days"] - agent_shortage) * 5.0
    # Local producer trade (+1 pt each)
    trade_boost = (agent_sales - base["producer_sales"]) * 1.0

    return round(hunger_saved + shortages_averted + trade_boost, 2)
