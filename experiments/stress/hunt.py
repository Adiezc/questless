# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Exploit hunt (M52.0): does any scripted attacker out-earn an honest player?

    uv run python experiments/stress/hunt.py              # 10 seeds, 120 days
    uv run python experiments/stress/hunt.py --seeds 20
    uv run python experiments/stress/hunt.py --policy \
        experiments/stress/policies/progressive_levy.toml

Five seeds is too few: on 5 seeds the squatter looked like an exploit in Drought (3/5) and the
hoarder didn't in Iron Shortage; on 10 both flipped.

Each attacker and the honest ``ScriptedPlayer`` (local strategy, from shock_vs_baseline.py) play
the same seed of each shipped shock scenario. Gain is coin per day plus held goods at today's
price, against the starting wallet. Harm is hungry NPC-days, against the honest run. Outputs in
experiments/results/: exploit_hunt.csv (one row per run) and exploit_hunt.md.

With ``--policy`` (M52.3), every player plays the scenario the policy extends ("before") and the
policy ("after") on the same seeds; an attacker that beats honest play on most seeds after but
not before is a new exploit the policy opened. Outputs: exploit_hunt_<policy>.{csv,md}.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import statistics as st
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "experiments" / "stress"))

import policy  # noqa: E402
from attackers import Flipper, Hoarder, Squatter  # noqa: E402
from shock_vs_baseline import ScriptedPlayer  # noqa: E402

from questless.api import Simulation  # noqa: E402
from questless.config import load_scenario  # noqa: E402
from questless.contracts.model import Status  # noqa: E402

RESULTS = ROOT / "experiments" / "results"
DAYS = 120
SCENARIOS = ("iron_shortage", "mine_disaster", "drought", "bandits")
HONEST = ("honest local", "honest importer")
PLAYERS = (*HONEST, "squatter", "hoarder", "flipper")
EXPLOIT_MARGIN = 1.25  # an attacker earning 25% more than honest on most seeds is an exploit


FINDINGS = """
## Findings (10 seeds, written by hand from the tables above)

- **No large exploit.** No attacker beats the better honest player by 25% on most seeds in more
  than one scenario.
- **Buying before a known shock** (hoarder) beats honest on 6/10 seeds in Iron Shortage, by a small
  margin (median 4.8 against 4.2 coin/day), and adds a median 40 hungry NPC-days: the ore it buys
  up is ore smiths can't. It earns nothing extra in the other scenarios. The shock schedule is in
  the scenario file, so a player can read it.
- **Claim and wait** (squatter) wins on 4/10 seeds everywhere. Accepted contracts aren't cancelled
  when the need goes away, but waiting for cheap prices doesn't pay enough to matter today.
- **Accept and abandon** (flipper) earns nothing: each abandon costs reputation (median -300) and
  a guild pays a distrusted player less.
"""


def make(name: str, sim: Simulation):
    return {
        "honest local": lambda: ScriptedPlayer(sim, "local"),
        "honest importer": lambda: ScriptedPlayer(sim, "importer"),
        "squatter": lambda: Squatter(sim),
        "hoarder": lambda: Hoarder(sim, ScriptedPlayer),
        "flipper": lambda: Flipper(sim),
    }[name]()


def config(source: str):
    """A shipped scenario by name, or ``before:<policy.toml>`` / ``after:<policy.toml>``."""
    side, _, path = source.partition(":")
    if side in ("before", "after"):
        return policy.load(path)[side == "after"]
    return load_scenario(ROOT / "scenarios" / f"{source}.toml")


def play(source: str, player: str, seed: int, days: int = DAYS) -> Simulation:
    sim = Simulation.from_scenario(dataclasses.replace(config(source), seed=seed))
    bot = make(player, sim)
    for _ in range(days):
        bot.act()
        sim.step()
    return sim


def run(job: tuple[str, str, int]) -> dict:
    scenario, player, seed = job
    sim = play(scenario, player, seed)
    cfg = sim.config
    me = sim.player()
    prices = sim.prices()
    worth = me["coin"] + sum(round(prices[g] * q) for g, q in me["goods"].items())
    mine = [c for c in sim.contracts() if c.accepted_by == "player" or c.status is Status.FULFILLED]
    return {
        "scenario": scenario,
        "player": player,
        "seed": seed,
        "gain_per_day": round((worth - cfg.player_wallet) / DAYS, 2),
        "fulfilled": sum(c.status is Status.FULFILLED for c in mine),
        "lapsed": sum(c.status is Status.EXPIRED and c.accepted_by == "player" for c in mine),
        "actions": len(sim.world.actions),
        "hungry_npc_days": sum(s.hungry_npcs for s in sim.world.stats),
        "reputation": sum(me["reputation"].values()),
    }


def score(rows: list[dict], source: str, player: str) -> tuple[list[dict], int, list[int]]:
    """The player's runs on ``source``, the seeds where it beats the better honest player by
    ``EXPLOIT_MARGIN``, and its harm (hungry NPC-days minus that honest run's) per seed."""
    by = {(r["scenario"], r["player"], r["seed"]): r for r in rows}
    seeds = sorted({r["seed"] for r in rows})
    rs = [by[(source, player, s)] for s in seeds]
    hs = [max((by[(source, h, s)] for h in HONEST), key=lambda r: r["gain_per_day"]) for s in seeds]
    pairs = list(zip(rs, hs, strict=True))
    beats = sum(r["gain_per_day"] > EXPLOIT_MARGIN * max(h["gain_per_day"], 0.01) for r, h in pairs)
    return rs, beats, [r["hungry_npc_days"] - h["hungry_npc_days"] for r, h in pairs]


def _cell(values) -> str:
    return f"{st.median(values):.1f} ({min(values):.1f} to {max(values):.1f})"


def summarise(rows: list[dict]) -> str:
    seeds = sorted({r["seed"] for r in rows})
    lines = [
        "# Exploit hunt (M52.0)\n",
        f"{len(seeds)} seeds, {DAYS} days. Median (range) per player. **Beats honest** counts the "
        f"seeds where the player's gain per day is above {EXPLOIT_MARGIN}x the better honest "
        "player's on the same seed (local or importer, both from `shock_vs_baseline.py`); most "
        "seeds means an exploit. Harm is hungry NPC-days minus that honest run's (negative means "
        "fewer hungry days). Generated by `experiments/stress/hunt.py`.\n",
    ]

    cell = _cell
    for scenario in SCENARIOS:
        lines += [
            f"\n## {scenario.replace('_', ' ').title()}\n",
            "| Player | Gain/day | Beats honest | Harm (hungry NPC-days) | Fulfilled | Lapsed "
            "| Reputation |",
            "|---|---|---|---|---|---|---|",
        ]
        for p in PLAYERS:
            rs, beats, harm = score(rows, scenario, p)
            flag = " **exploit**" if p not in HONEST and beats > len(seeds) / 2 else ""
            lines.append(
                f"| {p} | {cell([r['gain_per_day'] for r in rs])} | "
                f"{'-' if p in HONEST else f'{beats}/{len(seeds)}{flag}'} | "
                f"{'-' if p in HONEST else cell(harm)} | "
                f"{cell([r['fulfilled'] for r in rs])} | {cell([r['lapsed'] for r in rs])} | "
                f"{cell([r['reputation'] for r in rs])} |"
            )
    return "\n".join(lines) + "\n"


def summarise_policy(rows: list[dict], path: str) -> str:
    """Before and after, per attacker: a new exploit is one that wins on most seeds only after."""
    seeds = sorted({r["seed"] for r in rows})
    base, pol = policy.load(path)
    changes = policy.diff(base, pol)
    half = len(seeds) / 2
    lines = [
        f"# Policy stress test: {pol.name} (M52.3)\n",
        f"`{path}` against `{base.name}`, {len(seeds)} seeds, {DAYS} days. Generated by "
        "`experiments/stress/hunt.py --policy`.\n",
        "**Changes:**\n",
        *(f"- `{k}`: {a!r} → {b!r}" for k, (a, b) in changes.items()),
        "",
        "| Player | Gain/day before | Gain/day after | Beats honest before | Beats honest after "
        "| Harm after |",
        "|---|---|---|---|---|---|",
    ]
    found = []
    for p in PLAYERS:
        before, b_beats, _ = score(rows, f"before:{path}", p)
        after, a_beats, harm = score(rows, f"after:{path}", p)
        new = p not in HONEST and a_beats > half >= b_beats
        if new:
            found.append(p)
        attacker = p not in HONEST
        tag = " **new exploit**" if new else ""
        lines.append(
            f"| {p} | {_cell([r['gain_per_day'] for r in before])} | "
            f"{_cell([r['gain_per_day'] for r in after])} | "
            f"{f'{b_beats}/{len(seeds)}' if attacker else '-'} | "
            f"{f'{a_beats}/{len(seeds)}' if attacker else '-'}{tag} | "
            f"{_cell(harm) if attacker else '-'} |"
        )
    verdict = f"**New exploits: {', '.join(found)}.**" if found else "**No new exploit** found."
    return "\n".join([*lines, "", verdict]) + "\n"


def hunt(sources: list[str], seeds: int) -> list[dict]:
    jobs = [(src, p, s) for src in sources for p in PLAYERS for s in range(1, seeds + 1)]
    with ProcessPoolExecutor() as pool:
        return list(pool.map(run, jobs))


def _write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--policy", help="a policy TOML: compare it with the scenario it extends")
    args = parser.parse_args()
    RESULTS.mkdir(exist_ok=True)
    if args.policy:
        rows = hunt([f"before:{args.policy}", f"after:{args.policy}"], args.seeds)
        stem = f"exploit_hunt_{Path(args.policy).stem}"
        _write_csv(rows, RESULTS / f"{stem}.csv")
        report = summarise_policy(rows, args.policy)
        (RESULTS / f"{stem}.md").write_text(report)
        print(report)
        return
    rows = hunt(list(SCENARIOS), args.seeds)
    with (RESULTS / "exploit_hunt.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = summarise(rows) + FINDINGS
    (RESULTS / "exploit_hunt.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
