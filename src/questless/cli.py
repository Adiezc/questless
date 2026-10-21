# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Command-line entry point.

questless run scenarios/iron_shortage.toml            # contracts and why they exist
questless run scenarios/drought.toml --days 60 --json
questless run scenarios/baseline.toml --save saves/base.json
questless replay saves/base.json                      # rebuild and verify a save
questless demo                                        # open the interactive dashboard
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Sequence

from questless import __version__
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
    if args.command == "demo":
        return _demo(args)
    parser.print_help()
    return 0


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
    print(f"QUESTLESS · {cfg.name} · seed {cfg.seed} · {days} days in {elapsed:.2f}s")
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
