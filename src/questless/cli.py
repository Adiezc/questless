# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Command-line entry point.

questless run scenarios/iron_shortage.toml            # contracts and why they exist
questless run scenarios/drought.toml --days 60 --json
questless run scenarios/baseline.toml --save saves/base.json
questless replay saves/base.json                      # rebuild and verify a save
questless diff --base origin/main                     # economy impact of your changes
questless export scenarios/iron_shortage.toml --seeds 20 --out data/   # CSV tables for research
questless demo                                        # open the interactive dashboard
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from questless import __version__, bugreport
from questless.api import Simulation
from questless.persistence import ReplayMismatch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="questless", description="Emergent quests from living worlds."
    )
    parser.add_argument("--version", action="version", version=f"questless {__version__}")
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="run a scenario headless and list its contracts")
    run.add_argument("scenario", help="path to a scenario .toml")
    run.add_argument("--days", type=int, help="days to simulate (default: the scenario's)")
    run.add_argument("--seed", type=int, help="override the scenario seed")
    run.add_argument("--json", action="store_true", help="machine-readable output")
    run.add_argument("--save", metavar="PATH", help="write a save file at the end")
    run.add_argument("--brief", action="store_true", help="omit provenance chains")

    rep = sub.add_parser("replay", help="replay a save file and verify it reproduces exactly")
    rep.add_argument("save")

    dif = sub.add_parser(
        "diff",
        help="compare the economy against another commit (exit 1 on a failed check)",
    )
    dif.add_argument("--base", default="origin/main", help="git ref to compare against")
    dif.add_argument("--seeds", type=int, default=10, help="seeds per scenario (default 10)")
    dif.add_argument("--days", type=int, help="days per run (default: each scenario's own)")
    dif.add_argument("--workers", type=int, default=0, help="processes (default: one per CPU)")
    dif.add_argument("--out", default=".", help="where to write economy-diff.md and .json")
    dif.add_argument("--gates", help="gates file (default: .questless/ci.toml if present)")

    rp = sub.add_parser(
        "repro",
        help="replay a bug report and check its observation "
        "(exit 0 not reproduced, 1 reproduced, 2 replay mismatch)",
    )
    rp.add_argument("report")

    exp = sub.add_parser(
        "export", help="run a scenario and its policy arms over many seeds, as CSV for research"
    )
    exp.add_argument("scenario", help="path to a scenario .toml (the `base` arm)")
    exp.add_argument(
        "--policy",
        action="append",
        default=[],
        metavar="TOML",
        help="a policy that extends the scenario; one more arm each (repeatable)",
    )
    exp.add_argument(
        "--seeds", default="10", help="'20' for seeds 1-20, or '5-9', or '3,7,11' (default 10)"
    )
    exp.add_argument("--days", type=int, help="days per run (default: the scenario's)")
    exp.add_argument("--out", default="export", help="directory for the tables (default export/)")

    demo = sub.add_parser("demo", help="open the interactive dashboard (needs the demo extra)")
    demo.add_argument("--port", type=int, default=8501)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return _run(args)
    if args.command == "replay":
        return _replay(args)
    if args.command == "repro":
        return _repro(args)
    if args.command == "diff":
        return _diff(args)
    if args.command == "export":
        return _export(args)
    if args.command == "demo":
        return _demo(args)
    parser.print_help()
    return 0


def _diff(args: argparse.Namespace) -> int:
    """Run the scenario × seed grid on ``--base`` (in a temporary git worktree, with that commit's
    own engine) and on the working tree, then report what changed. Only scenarios present in both
    are compared."""
    import dataclasses
    import os
    import shutil
    import subprocess
    import tempfile

    from questless import diff

    def git(*a: str) -> str:
        return subprocess.run(
            ["git", *a], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()

    root = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True
        ).stdout.strip()
    )
    base = git("merge-base", args.base, "HEAD")
    changed = git("diff", "--name-only", base).splitlines()
    seeds = list(range(1, args.seeds + 1))
    workers = args.workers or None
    head_dir = root / "scenarios"
    with tempfile.TemporaryDirectory(prefix="questless-diff-") as tmp:
        tree = Path(tmp) / "base"
        git("worktree", "add", "--detach", str(tree), base)
        try:
            base_dir = tree / "scenarios"
            stems = sorted(
                {p.stem for p in head_dir.glob("*.toml")}
                & {p.stem for p in base_dir.glob("*.toml")}
            )
            # Run this version's grid code against the base commit's engine: copy it outside
            # both trees, and put the base's src first on the path.
            runner = Path(tmp) / "questless_grid.py"
            shutil.copy(diff.__file__, runner)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(runner),
                    *[str(base_dir / f"{s}.toml") for s in stems],
                    "--seeds",
                    ",".join(map(str, seeds)),
                    "--days",
                    str(args.days) if args.days else "default",
                    "--workers",
                    str(args.workers),
                ],
                env={**os.environ, "PYTHONPATH": str(tree / "src")},
                capture_output=True,
                text=True,
            )
            if proc.returncode:
                print(proc.stderr, file=sys.stderr)
                print(f"could not run the grid on {args.base} ({base[:7]})", file=sys.stderr)
                return 2
            base_rows = json.loads(proc.stdout)
        finally:
            git("worktree", "remove", "--force", str(tree))
    head_rows = diff.run_grid([head_dir / f"{s}.toml" for s in stems], seeds, args.days, workers)

    changes = diff.compare(base_rows, head_rows)
    gates = diff.load_gates(args.gates or root / ".questless" / "ci.toml")
    problems = [
        *diff.invariant_problems(head_rows),
        *diff.check_gates(changes, gates),
        *diff.determinism_problems(base_rows, head_rows, changed, head_dir, root),
    ]
    report = diff.render_markdown(
        changes, base_ref=args.base, seeds=len(seeds), scenarios=len(stems), problems=problems
    )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "economy-diff.md").write_text(report)
    finite = [
        {**dataclasses.asdict(c), "relative": c.relative if math.isfinite(c.relative) else None}
        for c in changes
    ]
    payload = {
        "base": args.base,
        "base_commit": base,
        "changed_paths": changed,
        "problems": problems,
        "changes": finite,
        "base_rows": base_rows,
        "head_rows": head_rows,
    }
    (out / "economy-diff.json").write_text(json.dumps(payload, indent=1) + "\n")
    print(report)
    return 1 if problems else 0


def _export(args: argparse.Namespace) -> int:
    from questless import export
    from questless.config import ConfigError

    try:
        seeds = export.parse_seeds(args.seeds)
    except ValueError:
        print(f"--seeds: expected '20', '5-9' or '3,7,11', got {args.seeds!r}", file=sys.stderr)
        return 2
    started = time.perf_counter()
    try:
        counts = export.export(
            args.scenario,
            args.out,
            seeds=seeds,
            policies=args.policy,
            days=args.days,
            command=" ".join(["questless", *sys.argv[1:]]),
        )
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2
    elapsed = time.perf_counter() - started
    print(f"{counts['runs']} runs in {elapsed:.1f}s -> {args.out}/")
    for table in ("daily", "npc_days", "events", "runs"):
        print(f"  {table}.csv  {counts[table]:>9,} rows")
    print("  codebook.md")
    return 0


def _repro(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.report).read_text())
    outcome = bugreport.repro(report)
    print(f"{outcome.status}: {outcome.message}")
    if report.get("note"):
        print(f"note: {report['note']}")
    return {bugreport.REPRODUCED: 1, bugreport.REPLAY_MISMATCH: 2}.get(outcome.status, 0)


def _run(args: argparse.Namespace) -> int:
    sim = Simulation.from_scenario(args.scenario, seed=args.seed)
    days = args.days if args.days is not None else sim.config.days
    started = time.perf_counter()
    sim.step(days)
    elapsed = time.perf_counter() - started
    if args.save:
        sim.save(args.save)
    if args.json:
        print(json.dumps(_as_json(sim, elapsed), indent=2))
        return 0

    cfg = sim.config
    print(f"Questless · {cfg.name} · seed {cfg.seed} · {days} days in {elapsed:.2f}s")
    if cfg.description:
        print(cfg.description)
    for shock in sim.world.modifiers.shocks:
        print(f"  shock: {shock.name}, day {shock.start}-{shock.end - 1}, x{shock.factor}")
    contracts = sim.contracts()
    print(f"\n{len(contracts)} contracts\n")
    for c in contracts:
        parent = f" · follows {c.parent_id}" if c.parent_id else ""
        print(
            f"{c.id}  day {c.created_tick:>3}  {c.kind.value:<12} {c.qty:>4} {c.good.value:<8}"
            f" reward {c.reward:>4}  [{c.status.value}]{parent}"
        )
        print(f"        {c.reason}")
        if not args.brief:
            for line in sim.explain(c.id):
                print(f"          · {line}")
        print()
    summary = sim.summary()
    print("suppressed:", ", ".join(f"{k} {v}" for k, v in sorted(summary["suppressed"].items())))
    print("state hash:", summary["state_hash"][:16])
    if args.save:
        print("saved:", args.save)
    return 0


def _demo(args: argparse.Namespace) -> int:
    import importlib.util
    import subprocess
    from pathlib import Path

    if importlib.util.find_spec("streamlit") is None:
        print("The demo needs Streamlit: uv sync --extra demo", file=sys.stderr)
        return 1
    app = Path(__file__).resolve().parents[2] / "app" / "streamlit_app.py"
    if not app.exists():
        print(f"Dashboard not found at {app}; run from a source checkout.", file=sys.stderr)
        return 1
    cmd = [sys.executable, "-m", "streamlit", "run", str(app), "--server.port", str(args.port)]
    return subprocess.call(cmd, cwd=app.parents[1])


def _replay(args: argparse.Namespace) -> int:
    started = time.perf_counter()
    try:
        sim = Simulation.load(args.save)
    except ReplayMismatch as exc:
        print(f"replay FAILED: {exc}", file=sys.stderr)
        return 1
    print(
        f"replayed {args.save}: day {sim.day}, {len(sim.world.actions)} player actions, "
        f"{len(sim.contracts())} contracts, state hash {sim.world.state_hash()[:16]} verified "
        f"in {time.perf_counter() - started:.2f}s"
    )
    return 0


def _as_json(sim: Simulation, elapsed: float) -> dict:
    return {
        "scenario": sim.config.name,
        "seed": sim.config.seed,
        "days": sim.day,
        "runtime_s": round(elapsed, 3),
        "summary": sim.summary(),
        "contracts": [
            {
                "id": c.id,
                "kind": c.kind.value,
                "status": c.status.value,
                "requester": c.requester,
                "funder": c.funder,
                "good": c.good.value,
                "qty": c.qty,
                "reward": c.reward,
                "created": c.created_tick,
                "deadline": c.deadline_tick,
                "parent": c.parent_id,
                "reason": c.reason,
                "why": sim.explain(c.id),
            }
            for c in sim.contracts()
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
