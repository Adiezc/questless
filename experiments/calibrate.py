# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Calibration report: does each scenario meet its targets across many seeds?

    uv run python experiments/calibrate.py            # 10 seeds
    uv run python experiments/calibrate.py --seeds 20

Targets (docs/PLAN.md section G.3):
- baseline: few contracts, stable prices (coefficient of variation < 0.25 for food and ore),
  low hunger, guards always paid
- shocks: first contract within 5-15 days of the shock; output recovers after the shock ends
"""

from __future__ import annotations

import argparse
import statistics as st
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from questless.api import Simulation  # noqa: E402
from questless.sim.ledger import Asset  # noqa: E402

SCENARIOS = {
    "baseline": None,
    "iron_shortage": Asset.IRON_ORE,
    "mine_disaster": Asset.IRON_ORE,
    "drought": Asset.FOOD,
    "bandits": Asset.FOOD,
}


def measure(name: str, seed: int, days: int = 120) -> dict:
    sim = Simulation.from_scenario(ROOT / "scenarios" / f"{name}.toml", seed=seed)
    started = time.perf_counter()
    sim.step(days)
    elapsed = time.perf_counter() - started
    stats = sim.world.stats
    contracts = sim.contracts()
    out = {
        "contracts": len(contracts),
        "hungry_avg": st.mean(s.hungry_npcs for s in stats[20:]),
        "unpaid_days": sum(1 for s in stats if s.wages_unpaid),
        "ms_per_tick": 1000 * elapsed / days,
        "price_cv": {
            str(g): st.pstdev(p := [s.prices[g] for s in stats[20:]]) / st.mean(p)
            for g in (Asset.FOOD, Asset.IRON_ORE, Asset.TOOLS)
        },
    }
    good = SCENARIOS[name]
    shocks = sim.world.modifiers.shocks
    if good is None or not shocks:
        return out
    start, end = shocks[0].start, shocks[0].end
    normal = st.mean(s.produced[good] for s in stats[max(start - 14, 0) : start])
    out["first_contract_delay"] = min(
        (c.created_tick - start for c in contracts if c.created_tick >= start), default=None
    )
    out["shortage_days"] = sum(
        1
        for s in stats
        if s.market[good].demand and s.market[good].unfilled > 0.1 * s.market[good].demand
    )
    recovered = next(
        (
            s.tick - end
            for s in stats[end:]
            if st.mean(x.produced[good] for x in stats[max(s.tick - 2, 0) : s.tick + 1])
            >= 0.9 * normal
        ),
        None,
    )
    out["recovery_days"] = recovered
    out["by_kind"] = {}
    for c in contracts:
        out["by_kind"][c.kind.value] = out["by_kind"].get(c.kind.value, 0) + 1
    return out


def report(seeds: list[int]) -> None:
    for name in SCENARIOS:
        rows = [measure(name, s) for s in seeds]

        def agg(key: str, rows=rows) -> str:
            vals = [r[key] for r in rows if r.get(key) is not None]
            if not vals:
                return "n/a"
            return f"median {st.median(vals):.1f}  range {min(vals):.0f}-{max(vals):.0f}"

        print(f"\n== {name} ({len(seeds)} seeds, 120 days)")
        print(f"  contracts            {agg('contracts')}")
        print(f"  hungry NPCs (avg)    {agg('hungry_avg')}")
        print(f"  unpaid wage days     {agg('unpaid_days')}")
        for good in ("food", "iron_ore", "tools"):
            cvs = [r["price_cv"][good] for r in rows]
            print(f"  price CV {good:<9}   median {st.median(cvs):.2f}  max {max(cvs):.2f}")
        if "first_contract_delay" in rows[0]:
            print(f"  first contract delay {agg('first_contract_delay')}")
            print(f"  shortage days        {agg('shortage_days')}")
            unrecovered = sum(1 for r in rows if r["recovery_days"] is None)
            print(f"  recovery after shock {agg('recovery_days')}  (not recovered: {unrecovered})")
            kinds: dict[str, int] = {}
            for r in rows:
                for k, v in r["by_kind"].items():
                    kinds[k] = kinds.get(k, 0) + v
            print(f"  contracts by kind    {kinds}")
        print(f"  ms per tick          {agg('ms_per_tick')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=10)
    report(list(range(1, parser.parse_args().seeds + 1)))
