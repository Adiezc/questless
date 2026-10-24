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

Every flagged exploit gets a findings section (M52.4): the attacker and seed, a saved replay in
experiments/results/exploits/ (``questless`` loads it like any save) and the coin flows that show
who paid for the attacker's gain.

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

from attackers import Flipper, Hoarder, Prober, Squatter  # noqa: E402
from shock_vs_baseline import ScriptedPlayer  # noqa: E402

from questless import policy  # noqa: E402
from questless.api import Simulation  # noqa: E402
from questless.config import load_scenario  # noqa: E402
from questless.contracts.model import Status  # noqa: E402
from questless.sim.entities import ESCROW, PLAYER  # noqa: E402
from questless.sim.ledger import Asset, EntryKind  # noqa: E402

RESULTS = ROOT / "experiments" / "results"
DAYS = 120
SCENARIOS = ("iron_shortage", "mine_disaster", "drought", "bandits")
HONEST = ("honest local", "honest importer")
PLAYERS = (*HONEST, "squatter", "hoarder", "flipper", "prober")
EXPLOIT_MARGIN = 1.25  # an attacker earning 25% more than honest on most seeds is an exploit


FINDINGS = """
## Findings (10 seeds, written by hand from the tables above)

- **No exploit.** No attacker beats the better honest player by 25% on most seeds anywhere.
- **Buying on the news of a shock** (hoarder) beats honest on 2/10 seeds in Iron Shortage. Before
  #93 it won on 6/10 by reading the schedule and buying the day before (12/20 when it bought on
  the announcement instead), adding 40-87 hungry NPC-days. The schedule is now hidden and a player
  may buy at most 25% of a good's sellable stock a day (`player.max_buy_share`).
- **Claim and wait** (squatter) wins on at most half the seeds in every scenario. Accepted
  contracts aren't cancelled when the need goes away, but waiting for cheap prices doesn't pay
  enough to matter today.
- **Accept and abandon** (flipper) earns nothing: each abandon costs reputation (median -300) and
  a guild pays a distrusted player less.
- **Deliver before sourcing** (prober) earns nothing except honest transport fees in Bandits: no
  rule pays for goods that weren't delivered. The planted-hole test (M52.5) checks it would.
"""


def make(name: str, sim: Simulation):
    return {
        "honest local": lambda: ScriptedPlayer(sim, "local"),
        "honest importer": lambda: ScriptedPlayer(sim, "importer"),
        "squatter": lambda: Squatter(sim),
        "hoarder": lambda: Hoarder(sim, ScriptedPlayer),
        "flipper": lambda: Flipper(sim),
        "prober": lambda: Prober(sim),
    }[name]()


def config(source: str):
    """A shipped scenario by name, or ``before:<policy.toml>`` / ``after:<policy.toml>``."""
    side, _, path = source.partition(":")
    if side in ("before", "after"):
        return policy.load(path)[side == "after"]
    return load_scenario(ROOT / "scenarios" / f"{source}.toml")


def play(
    source: str, player: str, seed: int, days: int = DAYS, flows: list | None = None
) -> Simulation:
    """One player's run. With ``flows``, every coin transfer to or from the player is appended to
    it as it happens (the ledger journal only keeps the most recent entries)."""
    sim = Simulation.from_scenario(dataclasses.replace(config(source), seed=seed))
    bot = make(player, sim)
    for _ in range(days):
        tick = sim.day
        bot.act()
        sim.step()
        if flows is not None:
            flows.extend(_player_coin(sim, tick))
    return sim


def _player_coin(sim: Simulation, tick: int) -> list:
    out = []
    for e in reversed(sim.world.ledger.journal):
        if e.tick < tick:
            break
        if e.kind is EntryKind.TRANSFER and e.asset is Asset.COIN and PLAYER in (e.src, e.dst):
            out.append(e)
    return out[::-1]


def _who(sim: Simulation, account: str, reason: str) -> str:
    """Name the party behind a coin flow: a contract's funder for escrow, else the account."""
    if account == ESCROW and reason in {c.id for c in sim.contracts()}:
        account = sim.contract(reason).funder
    if account in sim.world.npcs:
        return f"{sim.world.npcs[account].profession}s"
    return account


def finding(source: str, player: str, seed: int, honest_gain: float) -> str:
    """M52.4: one exploit as evidence: its replay and who paid for the gain."""
    flows: list = []
    sim = play(source, player, seed, flows=flows)
    label = source.replace(":", "_").replace("/", "_").replace(".toml", "")
    replay = RESULTS / "exploits" / f"{label}_{player}_seed{seed}.json"
    sim.save(replay)
    paid_in: dict[str, int] = {}
    paid_out: dict[str, int] = {}
    for e in flows:
        if e.dst == PLAYER:
            who = _who(sim, e.src, e.reason)
            paid_in[who] = paid_in.get(who, 0) + e.qty
        else:
            who = _who(sim, e.dst, e.reason)
            paid_out[who] = paid_out.get(who, 0) + e.qty
    gain = run((source, player, seed, DAYS))["gain_per_day"]
    shown = replay.relative_to(ROOT) if replay.is_relative_to(ROOT) else replay

    def listing(d: dict[str, int]) -> str:
        return ", ".join(f"{k} {v:,}" for k, v in sorted(d.items(), key=lambda kv: -kv[1]))

    return "\n".join(
        [
            f"\n### {player} on {source}, seed {seed}\n",
            f"- **Gain:** {gain} coin/day against {honest_gain} for the better honest player.",
            f"- **Replay:** `{shown}` (load with `Simulation.load`).",
            f"- **Coin in, by who paid:** {listing(paid_in) or 'none'}.",
            f"- **Coin out, by who received it:** {listing(paid_out) or 'none'}.",
        ]
    )


def findings(rows: list[dict], sources: list[str]) -> str:
    """A findings section for every (source, attacker) flagged as an exploit, on its best seed."""
    seeds = sorted({r["seed"] for r in rows})
    parts = []
    for source in sources:
        for p in PLAYERS:
            if p in HONEST:
                continue
            rs, beats, _ = score(rows, source, p)
            if beats <= len(seeds) / 2:
                continue
            honest = {
                s: max(
                    r["gain_per_day"]
                    for r in rows
                    if r["scenario"] == source and r["seed"] == s and r["player"] in HONEST
                )
                for s in seeds
            }
            best = max(rs, key=lambda r: r["gain_per_day"] - honest[r["seed"]])
            parts.append(finding(source, p, best["seed"], honest[best["seed"]]))
    if not parts:
        return ""
    return "\n## Exploit evidence (M52.4)\n" + "\n".join(parts) + "\n"


def run(job: tuple[str, str, int, int]) -> dict:
    scenario, player, seed, days = job
    sim = play(scenario, player, seed, days)
    cfg = sim.config
    me = sim.player()
    prices = sim.prices()
    worth = me["coin"] + sum(round(prices[g] * q) for g, q in me["goods"].items())
    mine = [c for c in sim.contracts() if c.accepted_by == "player" or c.status is Status.FULFILLED]
    return {
        "scenario": scenario,
        "player": player,
        "seed": seed,
        "gain_per_day": round((worth - cfg.player_wallet) / days, 2),
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


def hunt(
    sources: list[str], seeds: int, days: int = DAYS, workers: int | None = None
) -> list[dict]:
    """Every player on every source and seed. ``workers=1`` runs in this process (tests use it to
    plant a hole with monkeypatch); otherwise one process per CPU."""
    jobs = [(src, p, s, days) for src in sources for p in PLAYERS for s in range(1, seeds + 1)]
    if workers == 1:
        return [run(job) for job in jobs]
    with ProcessPoolExecutor(workers) as pool:
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
        report = summarise_policy(rows, args.policy) + findings(rows, [f"after:{args.policy}"])
        (RESULTS / f"{stem}.md").write_text(report)
        print(report)
        return
    rows = hunt(list(SCENARIOS), args.seeds)
    with (RESULTS / "exploit_hunt.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = summarise(rows) + FINDINGS + findings(rows, list(SCENARIOS))
    (RESULTS / "exploit_hunt.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
