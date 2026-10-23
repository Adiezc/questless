# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Economy diff (M23): what a change does to the economy, measured over scenarios and seeds.

Three building blocks, all standard library:

- ``suite_metrics(world)``: one run's outcome as a flat ``{name: number}`` dict;
- ``run_grid(scenarios, seeds, days)``: every scenario × seed, optionally in parallel processes;
- ``compare(base, head)``: runs paired by (scenario, seed), with a paired difference per metric
  that is flagged only when it beats the seed-to-seed noise (``significance``).

The ``questless diff --base <ref>`` command and the pull-request comment build on these (M23.3,
M23.5, M23.6).
"""

from __future__ import annotations

import dataclasses
import math
import statistics as st
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from questless.config import load_scenario
from questless.contracts.model import Status
from questless.sim.entities import ESCROW, TOWN
from questless.sim.ledger import GOODS, Asset
from questless.sim.world import World, build_world

REFERENCE_DAYS = slice(10, 15)  # after warm-up, before the shipped scenarios' shocks
SHORTAGE = 0.1  # unmet affordable demand above this share of demand is a shortage day
RECOVERED = 0.9  # a week's output back to this share of the reference means recovered
MIN_EFFECT = 0.03  # a significant change must also move the metric by at least 3%


def suite_metrics(world: World) -> dict[str, float]:
    """The run's outcome: prices, hunger, shortages, recovery, contracts and where the coin is."""
    stats = world.stats
    out: dict[str, float] = {}
    for good in GOODS:
        base = world.config.goods[good].base_price
        out[f"price_index.{good}"] = round(st.mean(s.prices[good] for s in stats) / base, 4)
        out[f"shortage_days.{good}"] = sum(
            1
            for s in stats
            if s.market[good].demand and s.market[good].unfilled > SHORTAGE * s.market[good].demand
        )
    out["hungry_npc_days"] = sum(s.hungry_npcs for s in stats)
    out["recovery_days"] = _recovery_days(world)
    contracts = list(world.contracts.contracts.values())
    out["contracts_posted"] = len(contracts)
    out["contracts_delivered"] = sum(c.status is Status.FULFILLED for c in contracts)
    ledger = world.ledger
    out["coin.town"] = ledger.balance(TOWN, Asset.COIN)
    out["coin.guilds"] = sum(ledger.balance(g.account, Asset.COIN) for g in world.guilds.values())
    out["coin.npcs"] = sum(ledger.balance(n.account, Asset.COIN) for n in world.npcs.values())
    out["coin.escrow"] = ledger.balance(ESCROW, Asset.COIN)
    return out


def _recovery_days(world: World) -> float:
    """Days from the last shock's end until a week's total output is back to ``RECOVERED`` of the
    reference days; 0 without shocks. A run that never recovers counts every remaining day."""
    if not world.modifiers.shocks:
        return 0
    end = max(s.end for s in world.modifiers.shocks)
    total = [sum(s.produced.values()) for s in world.stats]
    normal = st.mean(total[REFERENCE_DAYS]) if len(total) > REFERENCE_DAYS.stop else 0
    for t in range(max(end, 6), len(total)):
        if st.mean(total[t - 6 : t + 1]) >= RECOVERED * normal:
            return max(t - end, 0)
    return max(len(total) - end, 0)


def run_one(scenario: str, seed: int, days: int) -> dict[str, Any]:
    """One grid cell. A broken invariant ends the run and is reported, not raised."""
    cfg = dataclasses.replace(load_scenario(scenario), seed=seed)
    world = build_world(cfg)
    world.check_every_tick = True
    failure = None
    try:
        world.step(days)
    except AssertionError as exc:  # invariants raise AssertionError with the evidence
        failure = str(exc)
    metrics = suite_metrics(world)
    metrics["invariant_failures"] = 1 if failure else 0
    return {
        "scenario": Path(scenario).stem,
        "seed": seed,
        "metrics": metrics,
        "state_hash": world.state_hash(),
        "failure": failure,
    }


def run_grid(
    scenarios: list[str | Path], seeds: list[int], days: int, workers: int | None = 1
) -> list[dict[str, Any]]:
    """Every scenario × seed, sorted by (scenario, seed). ``workers`` > 1 (or ``None`` for one per
    CPU) runs them in separate processes; results are identical either way."""
    cells = [(str(sc), seed, days) for sc in scenarios for seed in seeds]
    if workers == 1:
        rows = [run_one(*cell) for cell in cells]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(run_one, *zip(*cells, strict=True)))
    return sorted(rows, key=lambda r: (r["scenario"], r["seed"]))


@dataclasses.dataclass(frozen=True)
class Change:
    scenario: str
    metric: str
    base_mean: float
    head_mean: float
    mean_diff: float  # head - base, paired by seed
    std_error: float
    relative: float  # mean_diff / |base_mean|; inf when the base is 0 and the head isn't
    significant: bool


def significance(
    base: list[float], head: list[float], min_effect: float = MIN_EFFECT
) -> tuple[float, float, bool]:
    """Paired difference (mean, standard error, significant). Significant means the mean
    difference is more than 2 standard errors from zero *and* at least ``min_effect`` of the base
    mean, so tiny but consistent shifts don't spam reviewers."""
    if len(base) != len(head) or not base:
        raise ValueError("base and head need the same, non-zero number of paired runs")
    diffs = [h - b for b, h in zip(base, head, strict=True)]
    mean = st.mean(diffs)
    se = st.stdev(diffs) / math.sqrt(len(diffs)) if len(diffs) > 1 else 0.0
    base_mean = st.mean(base)
    big_enough = abs(mean) >= min_effect * abs(base_mean) if base_mean else mean != 0
    beyond_noise = abs(mean) > 2 * se if se > 0 else mean != 0
    return mean, se, big_enough and beyond_noise


def compare(base: list[dict[str, Any]], head: list[dict[str, Any]]) -> list[Change]:
    """One ``Change`` per scenario and metric, pairing runs by (scenario, seed)."""
    base_by = {(r["scenario"], r["seed"]): r for r in base}
    head_by = {(r["scenario"], r["seed"]): r for r in head}
    if base_by.keys() != head_by.keys():
        raise ValueError("base and head grids cover different scenarios or seeds")
    changes = []
    for scenario in sorted({sc for sc, _ in base_by}):
        keys = sorted(k for k in base_by if k[0] == scenario)
        for metric in sorted(base_by[keys[0]]["metrics"]):
            b = [base_by[k]["metrics"][metric] for k in keys]
            h = [head_by[k]["metrics"].get(metric, math.nan) for k in keys]
            mean, se, significant = significance(b, h)
            base_mean = st.mean(b)
            relative = mean / abs(base_mean) if base_mean else (math.inf if mean else 0.0)
            changes.append(
                Change(scenario, metric, base_mean, st.mean(h), mean, se, relative, significant)
            )
    return changes
