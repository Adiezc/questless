# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Experiment: do player contracts help a shocked economy recover, and do guilds matter?

    uv run --extra experiments python experiments/shock_vs_baseline.py            # 10 seeds
    uv run --extra experiments python experiments/shock_vs_baseline.py --seeds 20

For each scenario (iron shortage, mine disaster, drought) and each seed, six arms run for
``DAYS`` days on identical seeds:

    baseline              no shock, no player
    shock                 the scenario's shock, nobody takes contracts
    shock+importer        a scripted player fulfils contracts, importing finished goods
    shock+local           a scripted player fulfils contracts, buying locally, importing only
                          raw goods (see ``ScriptedPlayer``)
    shock, no guilds      as "shock", with guilds disabled
    shock+local, no guilds

Outputs in experiments/results/: runs.csv (one row per run), summary.md (medians and ranges),
and two charts (output over time, shortage duration per arm).
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import statistics as st
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from questless.api import Simulation  # noqa: E402
from questless.bots import RAW, ScriptedPlayer  # noqa: E402, F401
from questless.config import load_scenario  # noqa: E402
from questless.contracts.model import Status  # noqa: E402
from questless.sim.ledger import Asset  # noqa: E402

RESULTS = ROOT / "experiments" / "results"
DAYS = 120
SCENARIOS = {
    "iron_shortage": Asset.IRON_ORE,
    "mine_disaster": Asset.IRON_ORE,
    "drought": Asset.FOOD,
}
ARMS = [
    "baseline",
    "shock",
    "shock+importer",
    "shock+local",
    "shock, no guilds",
    "shock+local, no guilds",
]


def simulate(scenario: str, arm: str, seed: int) -> tuple[Simulation, float]:
    cfg = dataclasses.replace(load_scenario(ROOT / "scenarios" / f"{scenario}.toml"), seed=seed)
    if arm == "baseline":
        cfg = dataclasses.replace(cfg, shocks=())
    if "no guilds" in arm:
        cfg = dataclasses.replace(cfg, guilds_enabled=False)
    sim = Simulation.from_scenario(cfg)
    strategy = "importer" if "importer" in arm else "local" if "local" in arm else None
    bot = ScriptedPlayer(sim, strategy) if strategy else None
    started = time.perf_counter()
    for _ in range(DAYS):
        if bot:
            bot.act()
        sim.step()
    return sim, time.perf_counter() - started


def measure(scenario: str, arm: str, seed: int, sim: Simulation, elapsed: float, base) -> dict:
    """Every outcome is measured against the no-shock run on the *same seed* (the counterfactual),
    over the window from the shock's start to the end of the run."""
    shock = load_scenario(ROOT / "scenarios" / f"{scenario}.toml").shocks[0]
    start, end = shock.start, shock.start + shock.duration
    good = SCENARIOS[scenario]
    stats = sim.world.stats
    produced = [s.produced[good] for s in stats]
    normal = [s.produced[good] for s in base.world.stats]

    def week(series, t):
        return st.mean(series[t - 6 : t + 1])

    recovery = next(
        (t - end for t in range(end, DAYS) if week(produced, t) >= 0.9 * week(normal, t)), None
    )
    contracts = sim.contracts()
    return {
        "scenario": scenario,
        "arm": arm,
        "seed": seed,
        "shortage_days": sum(
            1
            for s in stats[start:]
            if s.market[good].demand and s.market[good].unfilled > 0.1 * s.market[good].demand
        ),
        "recovery_days": recovery,
        "late_output_pct": round(
            100 * st.mean(produced[-30:]) / max(st.mean(normal[-30:]), 1e-9), 1
        ),
        "hungry_npc_days": sum(s.hungry_npcs for s in stats[start:]),
        "contracts_posted": len(contracts),
        "contracts_fulfilled": sum(c.status is Status.FULFILLED for c in contracts),
        "contracts_expired": sum(c.status is Status.EXPIRED for c in contracts),
        "invalid_contracts": sum(bool(sim.verify(c.id)) for c in contracts),
        "player_profit": sim.player()["coin"] - sim.config.player_wallet,
        "ms_per_tick": round(1000 * elapsed / DAYS, 2),
        "series": produced,
    }


def summarise(rows: list[dict]) -> str:
    def cell(values: list, fmt: str = "{:.0f}") -> str:
        values = [v for v in values if v is not None]
        if not values:
            return "n/a"
        return (
            f"{fmt.format(st.median(values))} ({fmt.format(min(values))}-{fmt.format(max(values))})"
        )

    lines = []
    for scenario in SCENARIOS:
        lines += [
            f"\n### {scenario.replace('_', ' ').title()}\n",
            "| Arm | Shortage days | Recovered (seeds) | Recovery days | Late output % of no-shock "
            "| Hungry NPC-days | Contracts posted | Fulfilled | Invalid |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for arm in ARMS:
            rs = [r for r in rows if r["scenario"] == scenario and r["arm"] == arm]
            if arm == "baseline":
                recovered = "n/a"
            else:
                recovered = f"{sum(r['recovery_days'] is not None for r in rs)}/{len(rs)}"

            def col(key: str, rs=rs) -> str:
                return cell([r[key] for r in rs])

            recovery = col("recovery_days") if arm != "baseline" else "n/a"
            lines.append(
                f"| {arm} | {col('shortage_days')} | {recovered} | {recovery} "
                f"| {col('late_output_pct')} | {col('hungry_npc_days')} "
                f"| {col('contracts_posted')} | {col('contracts_fulfilled')} "
                f"| {sum(r['invalid_contracts'] for r in rs)} |"
            )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=10)
    seeds = list(range(1, parser.parse_args().seeds + 1))
    RESULTS.mkdir(parents=True, exist_ok=True)

    rows = []
    started = time.perf_counter()
    for scenario in SCENARIOS:
        for seed in seeds:
            base, base_elapsed = simulate(scenario, "baseline", seed)
            rows.append(measure(scenario, "baseline", seed, base, base_elapsed, base))
            for arm in ARMS[1:]:
                sim, elapsed = simulate(scenario, arm, seed)
                rows.append(measure(scenario, arm, seed, sim, elapsed, base))
        print(f"{scenario}: done", flush=True)
    total = time.perf_counter() - started

    fields = [k for k in rows[0] if k != "series"]
    with (RESULTS / "runs.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: r[k] for k in fields} for r in rows)

    ms = st.median(r["ms_per_tick"] for r in rows)
    header = (
        f"# Experiment results\n\n{len(seeds)} seeds x {len(ARMS)} arms x "
        f"{len(SCENARIOS)} scenarios, "
        f"{DAYS} days each ({len(rows)} runs, {total:.0f}s total, median {ms} ms per simulated day "
        "incl. the scripted player).\nCells: median (min-max) across seeds. "
        "Every measure runs from "
        "the shock's first day; output and recovery are relative to the no-shock run on the same "
        "seed. Generated by "
        "`experiments/shock_vs_baseline.py`; raw rows in `runs.csv`.\n"
    )
    (RESULTS / "summary.md").write_text(header + summarise(rows) + "\n")
    print(header + summarise(rows))

    try:
        from charts import render

        render(rows, SCENARIOS, ARMS, RESULTS)
    except ImportError as exc:
        print(f"charts skipped ({exc}); install the 'experiments' extra")


if __name__ == "__main__":
    main()
