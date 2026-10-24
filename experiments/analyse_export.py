# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""A worked example of analysing a research export, using only the standard library.

    uv run questless export scenarios/iron_shortage.toml \\
        --policy experiments/stress/policies/progressive_levy.toml --seeds 20 --out data/
    uv run python experiments/analyse_export.py data/

Answers four questions a researcher would ask first, and prints them as Markdown:

1. **How fast does inequality spread?** The Gini's slope per 30 days, by arm.
2. **What does a policy change?** Paired by seed, so the difference is the policy's alone.
3. **Does concentration come before inefficiency?** Idle NPCs in the week after the most
   concentrated days of each run, against the week after the least concentrated.
4. **Does wealth stay put?** Rank correlation of NPC wealth on day 30 and on the last day; 1 means
   nobody changed places, the axis of the "Great Gatsby curve" (see docs/RESEARCH.md, M58).
5. **Capital against labour** (only with claims on): how much income is rent, and who owns the
   claims.

The same analyses take a few lines each in pandas, R or Stata; the CSVs load as they are.
"""

from __future__ import annotations

import csv
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

WEEK = 7


def main(folder: Path) -> None:
    daily = _read(folder / "daily.csv")
    runs = _read(folder / "runs.csv")
    npc_days = _read(folder / "npc_days.csv")
    by_run: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in daily:
        by_run[row["arm"], row["seed"]].append(row)
    arms = sorted({arm for arm, _ in by_run}, key=lambda a: (a != "base", a))

    print("## 1. Inequality over time\n")
    print("| Arm | Gini, first day | Gini, last day | Slope per 30 days |\n|---|---|---|---|")
    for arm in arms:
        slopes = [30 * _slope(rows, "coin_gini") for (a, _), rows in by_run.items() if a == arm]
        first = [rows[0]["coin_gini"] for (a, _), rows in by_run.items() if a == arm]
        last = [rows[-1]["coin_gini"] for (a, _), rows in by_run.items() if a == arm]
        print(f"| {arm} | {_mean_se(first)} | {_mean_se(last)} | {_mean_se(slopes, 4)} |")

    print("\n## 2. Each policy against the scenario, paired by seed\n")
    base = {r["seed"]: r for r in runs if r["arm"] == "base"}
    metrics = ("gini_end", "top10_end", "hungry_npc_days", "idle_npc_days", "output_value")
    if len(arms) == 1:
        print("Only the `base` arm was exported; add `--policy` to compare.")
    for arm in arms[1:]:
        print(f"**{arm} minus base** (mean ± standard error over seeds)\n")
        for metric in metrics:
            diffs = [r[metric] - base[r["seed"]][metric] for r in runs if r["arm"] == arm]
            print(f"- {metric}: {_mean_se(diffs, 4)}")
        print()

    print("## 3. Concentration, then idleness a week later\n")
    print("| Arm | After the most concentrated quarter of days | After the least |\n|---|---|---|")
    for arm in arms:
        high, low = [], []
        for (a, _), rows in by_run.items():
            if a != arm or len(rows) <= WEEK:
                continue
            ranked = sorted(range(len(rows) - WEEK), key=lambda i: rows[i]["coin_gini"])
            q = max(1, len(ranked) // 4)
            ahead = [st.fmean(r["idle_npcs"] for r in rows[i + 1 : i + 1 + WEEK]) for i in ranked]
            low.append(st.fmean(ahead[:q]))
            high.append(st.fmean(ahead[-q:]))
        print(f"| {arm} | {_mean_se(high, 1)} idle | {_mean_se(low, 1)} idle |")
    print(
        "\nA gap either way is a correlation, not a cause: a shock can move both at once. Check "
        "`events.csv`, and compare runs that differ only by policy (section 2), before reading "
        "it as one."
    )

    print("\n## 4. Wealth mobility\n")
    wealth: dict[tuple[str, int, int], dict[str, float]] = defaultdict(dict)
    for row in npc_days:
        wealth[row["arm"], row["seed"], row["day"]][row["npc_id"]] = row["wealth"]
    print("| Arm | Rank correlation, day 30 vs last day |\n|---|---|")
    for arm in arms:
        rhos = []
        for (a, seed), rows in by_run.items():
            if a == arm and len(rows) > 30:
                early, late = wealth[arm, seed, 30], wealth[arm, seed, rows[-1]["day"]]
                rhos.append(
                    _spearman([early[k] for k in sorted(early)], [late[k] for k in sorted(early)])
                )
        print(f"| {arm} | {_mean_se(rhos, 3) if rhos else 'runs too short'} |")

    if not any(r["claim_value"] for r in npc_days):
        return
    print("\n## 5. Capital against labour (land and mine claims, M60)\n")
    print("| Arm | Wealth Gini, last day | Rent share of NPC income | Claims held by top 10% |")
    print("|---|---|---|---|")
    for arm in arms:
        rows = [r for r in npc_days if r["arm"] == arm]
        rent = sum(r["rent_received"] for r in rows)
        labour = sum(r["produced_value"] for r in rows)
        last = [rs[-1] for (a, _), rs in by_run.items() if a == arm]
        if last[0]["wealth_gini"] == "":
            print(f"| {arm} | claims off | - | - |")
            continue
        wealth_gini = _mean_se([r["wealth_gini"] for r in last])
        top = _mean_se([r["claims_top10_share"] for r in last], 2)
        print(f"| {arm} | {wealth_gini} | {rent / (rent + labour):.1%} | {top} |")


def _read(path: Path) -> list[dict]:
    """Rows with numbers parsed: ints where possible, then floats, else the string."""
    with path.open(encoding="utf-8", newline="") as fh:
        return [{k: _num(v) for k, v in row.items()} for row in csv.DictReader(fh)]


def _num(text: str) -> int | float | str:
    for kind in (int, float):
        try:
            return kind(text)
        except ValueError:
            pass
    return text


def _slope(rows: list[dict], key: str) -> float:
    xs, ys = [r["day"] for r in rows], [r[key] for r in rows]
    return st.linear_regression(xs, ys).slope if len(rows) > 1 else 0.0


def _spearman(a: list[float], b: list[float]) -> float:
    """Pearson correlation of ranks (ties share their mean rank); works on Python 3.11."""
    return st.correlation(_ranks(a), _ranks(b))


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in order[i : j + 1]:
            ranks[k] = (i + j) / 2
        i = j + 1
    return ranks


def _mean_se(values: list[float], digits: int = 3) -> str:
    if len(values) < 2:
        return f"{values[0]:.{digits}f}" if values else "n/a"
    se = st.stdev(values) / len(values) ** 0.5
    return f"{st.fmean(values):.{digits}f} ± {se:.{digits}f}"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: analyse_export.py <export folder>")
    main(Path(sys.argv[1]))
