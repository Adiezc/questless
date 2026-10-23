# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Economy diff (M23): what a change does to the economy, measured over scenarios and seeds.

Three building blocks, all standard library:

- ``suite_metrics(world)``: one run's outcome as a flat ``{name: number}`` dict;
- ``run_grid(scenarios, seeds, days)``: every scenario × seed, optionally in parallel processes;
- ``compare(base, head)``: runs paired by (scenario, seed), with a paired difference per metric
  that is flagged only when it beats the seed-to-seed noise (``significance``).

On top of them: ``render_markdown`` (the pull-request comment, M23.5), ``check_gates`` (limits from
``.questless/ci.toml``, M23.7) and ``determinism_problems`` (M23.8). ``questless diff`` in
``cli.py`` runs the whole check against another commit (M23.3).

This module only imports engine parts that every version since v0.1 has, so ``cli.py`` can run it
as a script against an older checkout's code to build the base grid.
"""

from __future__ import annotations

import dataclasses
import fnmatch
import json
import math
import statistics as st
import sys
import tomllib
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


def run_one(scenario: str, seed: int, days: int | None) -> dict[str, Any]:
    """One grid cell (``days=None``: the scenario's own length). A broken invariant ends the run
    and is reported, not raised."""
    cfg = dataclasses.replace(load_scenario(scenario), seed=seed)
    world = build_world(cfg)
    world.check_every_tick = True
    failure = None
    try:
        world.step(cfg.days if days is None else days)
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
    scenarios: list[str | Path], seeds: list[int], days: int | None, workers: int | None = 1
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


# --- the pull-request comment (M23.5) ------------------------------------------------------------

MARKER = "<!-- questless-economy-diff -->"  # lets the workflow find and update its own comment
LABELS = {
    "hungry_npc_days": "Hungry NPC-days",
    "recovery_days": "Days to recover after the shock",
    "contracts_posted": "Contracts posted",
    "contracts_delivered": "Contracts delivered",
    "invariant_failures": "Invariant failures",
    "coin.town": "Town treasury",
    "coin.guilds": "Coin in guild treasuries",
    "coin.npcs": "Coin held by NPCs",
    "coin.escrow": "Coin in escrow",
}
MAX_BULLETS = 12


def label(metric: str) -> str:
    """The metric in plain words: "hungry_npc_days" -> "Hungry NPC-days"."""
    if metric in LABELS:
        return LABELS[metric]
    kind, _, good = metric.partition(".")
    good = good.replace("_", " ")
    return {
        "price_index": f"{good.capitalize()} price (× base price)",
        "shortage_days": f"{good.capitalize()} shortage days",
    }.get(kind, metric)


def _scenario_title(stem: str) -> str:
    return stem.replace("_", " ").title()


def _effect(c: Change) -> str:
    if c.base_mean and c.head_mean / c.base_mean >= 2:
        return f"**{c.head_mean / c.base_mean:.1f}×**"
    if math.isinf(c.relative):
        return "**new**"
    return f"**{c.relative:+.0%}**"


def render_markdown(
    changes: list[Change],
    *,
    base_ref: str,
    seeds: int,
    scenarios: int,
    problems: tuple[str, ...] | list[str] = (),
) -> str:
    """The comment: problems first, then significant changes in plain words, then a full table."""
    lines = [
        MARKER,
        f"### Economy impact ({seeds} seeds × {scenarios} scenarios, against `{base_ref}`)",
        "",
    ]
    if problems:
        lines += ["**Failed checks:**", *[f"- {p}" for p in problems], ""]
    significant = sorted(
        (c for c in changes if c.significant),
        key=lambda c: -abs(c.relative) if not math.isinf(c.relative) else -math.inf,
    )
    if significant:
        for c in significant[:MAX_BULLETS]:
            lines.append(
                f"- {label(c.metric)} in {_scenario_title(c.scenario)}: "
                f"{_num(c.base_mean)} → {_num(c.head_mean)} ({_effect(c)})"
            )
        if len(significant) > MAX_BULLETS:
            lines.append(f"- …and {len(significant) - MAX_BULLETS} more in the table below")
    else:
        lines.append("No significant change in any metric.")
    moved = [c for c in changes if c.mean_diff]
    lines += ["", "<details><summary>Every metric that moved</summary>", ""]
    if moved:
        lines += [
            "| Scenario | Metric | Base | Head | Change | Significant |",
            "|---|---|---|---|---|---|",
            *[
                f"| {_scenario_title(c.scenario)} | {label(c.metric)} | {_num(c.base_mean)} | "
                f"{_num(c.head_mean)} | {c.relative:+.1%} | {'yes' if c.significant else 'no'} |"
                for c in moved
            ],
        ]
    else:
        lines.append("Nothing moved: every metric is identical on every seed.")
    lines += [
        "",
        "</details>",
        "",
        "<sub>Runs are paired by seed. A change is significant when it is more than 2 standard "
        "errors from zero and at least 3% of the base. Generated by `questless diff`.</sub>",
    ]
    return "\n".join(lines) + "\n"


def _num(x: float) -> str:
    return f"{x:,.0f}" if abs(x) >= 100 else f"{x:,.2f}".rstrip("0").rstrip(".")


# --- gates (M23.7) -------------------------------------------------------------------------------


def load_gates(path: str | Path) -> dict[str, dict[str, float]]:
    """``[gates]`` from ``.questless/ci.toml``: ``"metric glob" = { max_ratio = 1.2 }`` and/or
    ``min_ratio``. A missing file means no gates."""
    path = Path(path)
    if not path.exists():
        return {}
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    gates = data.get("gates", {})
    for pattern, limits in gates.items():
        if not isinstance(limits, dict) or not limits.keys() <= {"max_ratio", "min_ratio"}:
            raise ValueError(f"{path}: gate {pattern!r} takes max_ratio and/or min_ratio")
    return gates


def check_gates(changes: list[Change], gates: dict[str, dict[str, float]]) -> list[str]:
    """One message per significant change that breaks a gate (head ÷ base outside its limits)."""
    out = []
    for c in changes:
        if not c.significant or not c.base_mean:
            continue
        ratio = c.head_mean / c.base_mean
        for pattern, limits in sorted(gates.items()):
            if not fnmatch.fnmatchcase(c.metric, pattern):
                continue
            if ratio > limits.get("max_ratio", math.inf) or ratio < limits.get("min_ratio", 0):
                out.append(
                    f"{label(c.metric)} in {_scenario_title(c.scenario)} is {ratio:.2f}× the base "
                    f"({_num(c.base_mean)} → {_num(c.head_mean)}); gate `{pattern}` allows "
                    f"{_allowed(limits)}"
                )
    return out


def _allowed(limits: dict[str, float]) -> str:
    low, high = limits.get("min_ratio"), limits.get("max_ratio")
    if low is not None and high is not None:
        return f"{low}× to {high}×"
    return f"up to {high}×" if high is not None else f"at least {low}×"


def invariant_problems(rows: list[dict[str, Any]]) -> list[str]:
    return [
        f"Invariant broken in {_scenario_title(r['scenario'])}, seed {r['seed']}: {r['failure']}"
        for r in rows
        if r["failure"]
    ]


# --- determinism (M23.8) -------------------------------------------------------------------------


def scenario_files(path: str | Path) -> list[Path]:
    """A scenario file and every file it ``extends``, nearest first."""
    out: list[Path] = []
    path = Path(path).resolve()
    while path not in out:
        out.append(path)
        with path.open("rb") as fh:
            parent = tomllib.load(fh).get("scenario", {}).get("extends")
        if parent is None:
            break
        path = (path.parent / parent).resolve()
    return out


def determinism_problems(
    base: list[dict[str, Any]],
    head: list[dict[str, Any]],
    changed_paths: list[str],
    scenario_dir: str | Path,
    repo_root: str | Path,
) -> list[str]:
    """With the engine unchanged, a scenario whose files didn't change must replay to the same
    state hash on every seed; anything else is accidental non-determinism."""
    if any(p.startswith("src/questless/") for p in changed_paths):
        return []
    root = Path(repo_root).resolve()
    changed = {(root / p).resolve() for p in changed_paths}
    head_by = {(r["scenario"], r["seed"]): r for r in head}
    out = []
    for r in base:
        other = head_by.get((r["scenario"], r["seed"]))
        if other is None or other["state_hash"] == r["state_hash"]:
            continue
        files = scenario_files(Path(scenario_dir) / f"{r['scenario']}.toml")
        if not changed & set(files):
            out.append(
                f"{_scenario_title(r['scenario'])}, seed {r['seed']}: the state hash changed "
                "although neither the engine nor the scenario did (non-determinism?)"
            )
    return out


# --- worker mode: ``python diff.py SCENARIO... --seeds 1,2 --days N`` prints the grid as JSON ----


def _main(argv: list[str]) -> None:
    seeds = [int(s) for s in argv[argv.index("--seeds") + 1].split(",")]
    days_arg = argv[argv.index("--days") + 1]
    workers = int(argv[argv.index("--workers") + 1]) or None  # 0: one per CPU
    scenarios = argv[: argv.index("--seeds")]
    days = None if days_arg == "default" else int(days_arg)
    json.dump(run_grid(scenarios, seeds, days, workers), sys.stdout)


if __name__ == "__main__":
    _main(sys.argv[1:])
