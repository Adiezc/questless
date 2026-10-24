# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Research export: every run of a scenario and its policy arms, as plain CSV tables.

    questless export scenarios/iron_shortage.toml \\
        --policy experiments/stress/policies/progressive_levy.toml --seeds 20 --out data/

writes, for every arm × seed:

- ``daily.csv``: one row per day, town-wide (prices, output, hunger, coin concentration);
- ``npc_days.csv``: one row per NPC per day (wallet, goods, wealth, what they made and traded);
- ``events.csv``: when each shock started and ended, and which rules each policy arm changed;
- ``runs.csv``: one row per run, with headline outcomes and the state hash that reproduces it;
- ``codebook.md``: what every column means, and how the files were made.

Arms share seeds, so arm A seed 7 and arm B seed 7 start from the same world and differ only in
their rules: subtract them pairwise to measure a policy's effect. The engine isn't changed; NPCs are
read after each day, so exporting a run leaves its state hash exactly as a plain run.
"""

from __future__ import annotations

import csv
import dataclasses
import sys
from collections.abc import Iterator, Sequence
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from questless import __version__, policy
from questless.api import Simulation
from questless.bots import STRATEGIES, ScriptedPlayer
from questless.config import ConfigError, ScenarioConfig, load_scenario
from questless.contracts.model import Status
from questless.sim.entities import PLAYER
from questless.sim.ledger import GOODS, Asset, Entry
from questless.sim.world import World

DAILY = [
    "arm",
    "seed",
    "day",
    "coin_gini",
    "coin_top10_share",
    "npc_coin",
    "npc_wealth",
    "hungry_npcs",
    "idle_npcs",
    "live_contracts",
    "upkeep",
    "levy_evaded",
    "levy_thresholds",
    "wages_paid",
    "wages_unpaid",
    "legitimacy",
    *(f"{col}_{g}" for g in map(str, GOODS) for col in ("price", "produced", "traded", "unfilled")),
]
NPC_DAYS = [
    "arm",
    "seed",
    "day",
    "npc_id",
    "profession",
    "site",
    "guild",
    "skill",
    "thrift",
    "state",
    "hunger",
    "tool_condition",
    "coin",
    "coin_change",
    "goods_value",
    "wealth",
    "produced_units",
    "produced_value",
    "consumed_units",
    "bought_units",
    "sold_units",
    "unmet_units",
    "idle",
]
EVENTS = ["arm", "seed", "kind", "name", "start_day", "end_day", "detail"]
PLAYER_DAYS = [
    "arm",
    "seed",
    "day",
    "strategy",
    "coin",
    "goods_value",
    "wealth",
    "accepted",
    "delivered_total",
    "caravans_pending",
]
TRANSACTIONS = ["arm", "seed", "day", "kind", "asset", "qty", "src", "dst", "reason"]
RUNS = [
    "arm",
    "seed",
    "scenario",
    "days",
    "npcs",
    "gini_start",
    "gini_end",
    "gini_max",
    "top10_end",
    "hungry_npc_days",
    "idle_npc_days",
    "output_value",
    "contracts_posted",
    "contracts_fulfilled",
    "player",
    "player_profit",
    "state_hash",
]


@dataclasses.dataclass(frozen=True)
class Arm:
    name: str
    config: ScenarioConfig
    changes: dict[str, tuple[Any, Any]]  # rule -> (scenario's value, this arm's value); no names


def arms(scenario: str | Path, policies: Sequence[str | Path]) -> list[Arm]:
    """The scenario as the ``base`` arm, then one arm per policy, named after its file.

    Each policy must extend ``scenario`` and change only its rules (see ``policy.load``), so arms
    differ in their rules and nothing else.
    """
    base = load_scenario(scenario)
    out = [Arm("base", base, {})]
    for path in policies:
        parent, cfg = policy.load(path)
        if parent != base:
            raise ConfigError(f"{path}: extends a different scenario than {scenario}")
        name = Path(path).stem
        if name in {a.name for a in out}:
            raise ConfigError(f"{path}: two arms named {name!r}")
        changes = {k: v for k, v in policy.diff(base, cfg).items() if not k.startswith("scenario.")}
        out.append(Arm(name, cfg, changes))
    return out


def export(
    scenario: str | Path,
    out: str | Path,
    *,
    seeds: list[int],
    policies: Sequence[str | Path] = (),
    days: int | None = None,
    player: str | None = None,
    transactions: bool = False,
    command: str | None = None,
) -> dict[str, int]:
    """Run every arm on every seed and write the tables to ``out``. Returns rows per table.

    ``player`` puts a scripted player (``bots.STRATEGIES``) in every run, acting before each day
    as a human would, and adds ``player_days.csv``. ``transactions`` adds ``transactions.csv``,
    every ledger entry of the run (large: several hundred rows per day).
    """
    if player is not None and player not in STRATEGIES:
        raise ConfigError(f"player: expected one of {', '.join(STRATEGIES)}, got {player!r}")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    tables = {"daily": DAILY, "npc_days": NPC_DAYS, "events": EVENTS, "runs": RUNS}
    if player:
        tables["player_days"] = PLAYER_DAYS
    if transactions:
        tables["transactions"] = TRANSACTIONS
    counts = dict.fromkeys(tables, 0)
    all_arms = arms(scenario, policies)
    with ExitStack() as stack:
        w = {
            name: stack.enter_context(_table(out / f"{name}.csv", h)) for name, h in tables.items()
        }
        for arm in all_arms:
            for seed in seeds:
                sim = Simulation.from_scenario(dataclasses.replace(arm.config, seed=seed))
                world = sim.world
                bot = ScriptedPlayer(sim, player) if player else None
                coin = {
                    n.id: world.ledger.balance(n.account, Asset.COIN) for n in world.npcs.values()
                }
                key = [arm.name, seed]
                for _ in range(days if days is not None else world.config.days):
                    mark = world.ledger.journal[-1] if world.ledger.journal else None
                    if bot:
                        bot.act()
                    sim.step()
                    rows = list(_npc_rows(world, coin))
                    w["npc_days"].writerows([*key, *r] for r in rows)
                    w["daily"].writerow([*key, *_daily_row(world, rows)])
                    counts["npc_days"] += len(rows)
                    counts["daily"] += 1
                    if bot:
                        w["player_days"].writerow([*key, *_player_row(sim, player)])
                        counts["player_days"] += 1
                    if transactions:
                        entries = _entries_since(world, mark)
                        w["transactions"].writerows([*key, *e] for e in entries)
                        counts["transactions"] += len(entries)
                event_rows = _event_rows(world, arm)
                w["events"].writerows([*key, *r] for r in event_rows)
                w["runs"].writerow([*key, *_run_row(sim, player)])
                counts["events"] += len(event_rows)
                counts["runs"] += 1
    (out / "codebook.md").write_text(
        _codebook(scenario, all_arms, seeds, command, tables), encoding="utf-8"
    )
    return counts


def parse_seeds(text: str) -> list[int]:
    """``"20"`` is seeds 1-20 (as ``questless diff``), ``"5-9"`` a range, ``"3,7,11"`` a list."""
    if text.isdigit():
        return list(range(1, int(text) + 1))
    seeds: list[int] = []
    for part in text.split(","):
        lo, _, hi = part.partition("-")
        seeds.extend(range(int(lo), int(hi or lo) + 1))
    return sorted(set(seeds))


# --- rows ---------------------------------------------------------------------------------------


def _npc_rows(world: World, coin: dict[str, int]) -> Iterator[list[Any]]:
    """End-of-day rows for every NPC; updates ``coin`` to today's balances."""
    stats = world.stats[-1]
    prices = stats.prices
    for npc in world.npcs_in_order():
        rec = npc.history[-1] if npc.history and npc.history[-1].tick == stats.tick else None
        held: dict[Asset, int] = {}
        # Market workers' site is their own account: count it once (as ``eat`` does).
        for account in dict.fromkeys((npc.account, npc.site_account)):
            for asset, qty in world.ledger.holdings(account).items():
                held[asset] = held.get(asset, 0) + qty
        wallet = held.pop(Asset.COIN, 0)
        goods_value = sum(qty * prices.get(asset, 0.0) for asset, qty in held.items())
        produced = rec.produced if rec else {}
        yield [
            stats.tick,
            npc.id,
            str(npc.profession),
            str(npc.site),
            npc.guild_id or "",
            npc.traits.skill,
            npc.traits.thrift,
            str(npc.state),
            npc.hunger,
            round(npc.tool_condition, 4),
            wallet,
            wallet - coin[npc.id],
            round(goods_value, 2),
            round(wallet + goods_value, 2),
            sum(produced.values()),
            round(sum(q * prices.get(a, 0.0) for a, q in produced.items()), 2),
            sum(rec.consumed.values()) if rec else 0,
            sum(rec.bought.values()) if rec else 0,
            sum(rec.sold.values()) if rec else 0,
            sum(rec.unmet.values()) if rec else 0,
            int(rec.idle) if rec else 0,
        ]
        coin[npc.id] = wallet


def _daily_row(world: World, npc_rows: list[list[Any]]) -> list[Any]:
    s = world.stats[-1]
    coin_col, wealth_col = NPC_DAYS.index("coin") - 2, NPC_DAYS.index("wealth") - 2
    per_good: list[Any] = []
    for good in GOODS:
        market = s.market.get(good)
        per_good += [
            round(s.prices[good], 2),
            s.produced.get(good, 0),
            market.traded if market else 0,
            market.unfilled if market else 0,
        ]
    return [
        s.tick,
        round(s.coin_gini, 4),
        round(s.coin_top10_share, 4),
        sum(r[coin_col] for r in npc_rows),
        round(sum(r[wealth_col] for r in npc_rows), 2),
        s.hungry_npcs,
        s.idle_npcs,
        s.contracts.live if s.contracts else 0,
        s.upkeep,
        s.levy_evaded,
        ";".join(map(str, s.levy_thresholds)),
        s.wages_paid,
        s.wages_unpaid,
        "" if s.legitimacy is None else round(s.legitimacy, 4),
        *per_good,
    ]


def _event_rows(world: World, arm: Arm) -> list[list[Any]]:
    rows: list[list[Any]] = [
        ["policy", knob, 0, "", f"{before!r} -> {after!r}"]
        for knob, (before, after) in arm.changes.items()
    ]
    for shock in world.modifiers.shocks:
        site = f" at {shock.site}" if shock.site else ""
        detail = f"{shock.effect} x{shock.factor}{site} ({shock.source})"
        rows.append(["shock", shock.name, shock.start, shock.end, detail])
    return rows


def _run_row(sim: Simulation, player: str | None) -> list[Any]:
    world, stats = sim.world, sim.world.stats
    gini = [s.coin_gini for s in stats] or [0.0]
    statuses = [str(c.status) for c in sim.contracts()]
    output = sum(qty * s.prices.get(good, 0.0) for s in stats for good, qty in s.produced.items())
    return [
        world.config.name,
        len(stats),
        len(world.npcs),
        round(gini[0], 4),
        round(gini[-1], 4),
        round(max(gini), 4),
        round(stats[-1].coin_top10_share, 4) if stats else 0.0,
        sum(s.hungry_npcs for s in stats),
        sum(s.idle_npcs for s in stats),
        round(output, 2),
        len(statuses),
        statuses.count("fulfilled"),
        player or "",
        _player_coin(world) - world.config.player_wallet if player else "",
        world.state_hash(),
    ]


def _player_coin(world: World) -> int:
    return world.ledger.balance(PLAYER, Asset.COIN)


def _player_row(sim: Simulation, strategy: str | None) -> list[Any]:
    world, prices = sim.world, sim.world.stats[-1].prices
    held = world.ledger.holdings(PLAYER)
    wallet = held.get(Asset.COIN, 0)
    goods = sum(q * prices.get(a, 0.0) for a, q in held.items() if a is not Asset.COIN)
    delivered = sum(c.accepted_by == PLAYER for c in sim.contracts(str(Status.FULFILLED)))
    return [
        world.stats[-1].tick,
        strategy,
        wallet,
        round(goods, 2),
        round(wallet + goods, 2),
        len(sim.contracts("accepted")),
        delivered,
        len(world.pending_caravans),
    ]


def _entries_since(world: World, mark: Entry | None) -> list[list[Any]]:
    """Ledger entries appended after ``mark``, oldest first. Fails rather than drop any: if the
    journal rolled past ``mark`` in a single day, the day had more entries than it keeps."""
    journal = world.ledger.journal
    fresh: list[Entry] = []
    for entry in reversed(journal):
        if entry is mark:
            break
        fresh.append(entry)
    else:
        if mark is not None:
            raise RuntimeError(
                f"day {world.stats[-1].tick}: more ledger entries than the journal keeps"
            )
    return [
        [e.tick, str(e.kind), str(e.asset), e.qty, e.src or "", e.dst or "", e.reason]
        for e in reversed(fresh)
    ]


class _table:
    """A CSV file with a header row, opened for the duration of a ``with`` block."""

    def __init__(self, path: Path, header: list[str]) -> None:
        self.path, self.header = path, header

    def __enter__(self) -> Any:
        self.fh = self.path.open("w", newline="", encoding="utf-8")
        writer = csv.writer(self.fh)
        writer.writerow(self.header)
        return writer

    def __exit__(self, *exc: object) -> None:
        self.fh.close()


# --- codebook -----------------------------------------------------------------------------------

COLUMNS: dict[str, dict[str, str]] = {
    "daily.csv": {
        "arm": "`base` (the scenario as written) or the policy file's name.",
        "seed": "Random seed. Same seed in two arms = same starting world.",
        "day": "Day number, from 0. Values are at the end of the day.",
        "coin_gini": "Gini of NPC coin after the market clears: 0 equal, (n-1)/n one holds all.",
        "coin_top10_share": "Share of NPC coin held by the richest 10% of NPCs (at least one).",
        "npc_coin": "Coin held by all NPCs at the end of the day.",
        "npc_wealth": "NPC coin plus goods held, valued at the day's prices.",
        "hungry_npcs": "NPCs whose hunger passed the scenario's `hungry_after` today.",
        "idle_npcs": "NPCs who could not work today for lack of inputs.",
        "live_contracts": "Contracts open on the quest board at the end of the day.",
        "upkeep": "Town levy collected today, in coin.",
        "levy_evaded": "Levy NPCs did not pay because legitimacy was low (0 when that is off).",
        "levy_thresholds": "Today's levy bracket thresholds in coin, `;`-separated; blank if flat.",
        "wages_paid": "Guard wages the town paid today, in coin.",
        "wages_unpaid": "Guard wages owed but not paid today, in coin.",
        "legitimacy": "The town's authority, 0-1; blank when the feature is off.",
        "price_<good>": "Market price after today's adjustment, in coin per unit.",
        "produced_<good>": "Units produced today, town-wide.",
        "traded_<good>": "Units that changed hands at market today.",
        "unfilled_<good>": "Units bid for today that no seller supplied.",
    },
    "npc_days.csv": {
        "arm, seed, day": "As in daily.csv.",
        "npc_id": "Stable id, e.g. `npc_042`; the same NPC across days, arms and seeds.",
        "profession": "miner, farmer, smith or guard; fixed for life.",
        "site": "Where the NPC works.",
        "guild": "Guild id, or blank.",
        "skill": "Production multiplier, drawn at genesis.",
        "thrift": "Share of wallet the NPC holds back as a cash reserve, 0-1.",
        "state": "working, idle_no_input, idle_no_demand, hungry or waiting_on_contract.",
        "hunger": "Days in a row without enough food.",
        "tool_condition": "Condition of tools (workers) or weapons (guards), 0-1.",
        "coin": "Coin at the end of the day.",
        "coin_change": "Coin today minus coin yesterday (or at genesis on day 0): net income.",
        "goods_value": "Goods held at market and at the work site, at the day's prices.",
        "wealth": "coin + goods_value.",
        "produced_units / produced_value": "Output today, in units and at the day's prices.",
        "consumed_units": "Units eaten or used up as inputs today.",
        "bought_units / sold_units": "Units bought and sold at market today.",
        "unmet_units": "Units needed today but not on hand.",
        "idle": "1 if the NPC could not work at all today.",
    },
    "events.csv": {
        "arm, seed": "As in daily.csv.",
        "kind": "`shock` (a disaster or boom) or `policy` (a rule the arm changed).",
        "name": "The shock's name, or the dotted config knob the policy changed.",
        "start_day": "First day the shock applies; 0 for policies (they apply from genesis).",
        "end_day": "First day the shock no longer applies (exclusive); blank for policies.",
        "detail": "Shock effect, factor and site, or the knob's `base -> arm` values.",
    },
    "player_days.csv": {
        "arm, seed, day": "As in daily.csv.",
        "strategy": "`local` (buys at market, imports only food and ore) or `importer` (caravans "
        "first). Both are greedy and honest, and use only the public API.",
        "coin": "The player's coin at the end of the day.",
        "goods_value": "Goods the player holds, at the day's prices.",
        "wealth": "coin + goods_value.",
        "accepted": "Quests the player has accepted and not yet delivered.",
        "delivered_total": "Quests the player has delivered so far.",
        "caravans_pending": "Caravans the player ordered that have not arrived yet.",
    },
    "transactions.csv": {
        "arm, seed": "As in daily.csv.",
        "day": "Day of the entry, from day 0; starting balances are not entries. Caravans unload "
        "at the start of the next day, so a few entries carry the next day's number.",
        "kind": "transfer, produce or consume.",
        "asset": "coin or a good.",
        "qty": "Units moved, made or used up.",
        "src / dst": "Accounts: an NPC id, `npc_042@mine` (output waiting at a site), `town`, "
        "`market`, `escrow`, `guild:<id>`, `player`, `outside` or `in_transit`; blank for produce "
        "(no source) and consume (no destination).",
        "reason": "Why, e.g. `upkeep`, `guard wage`, `sale to player`, `caravan`.",
    },
    "runs.csv": {
        "arm, seed": "As in daily.csv.",
        "scenario": "The scenario's name as written in its file.",
        "days": "Days simulated.",
        "npcs": "NPCs in the world.",
        "gini_start / gini_end / gini_max": "coin_gini on the first day, last day and its peak.",
        "top10_end": "coin_top10_share on the last day.",
        "hungry_npc_days / idle_npc_days": "Sum over days of hungry_npcs and idle_npcs.",
        "output_value": "Everything produced over the run, valued at each day's prices.",
        "contracts_posted / contracts_fulfilled": "Quests that appeared, and those delivered.",
        "player": "The scripted player's strategy (`--player`), or blank: then nobody can "
        "deliver a quest, so every one expires.",
        "player_profit": "The player's final coin minus their starting wallet; blank without one.",
        "state_hash": "SHA-256 of the final world; rerunning arm + seed must reproduce it.",
    },
}


def _codebook(
    scenario: str | Path,
    all_arms: list[Arm],
    seeds: list[int],
    command: str | None,
    tables: dict[str, list[str]],
) -> str:
    lines = [
        "# Questless research export",
        "",
        f"- **Scenario:** `{scenario}`",
        f"- **Arms:** {', '.join(f'`{a.name}`' for a in all_arms)}",
        f"- **Seeds:** {_ranges(seeds)} ({len(seeds)} per arm)",
        f"- **Made with:** questless {__version__}, Python {sys.version.split()[0]}",
    ]
    if command:
        lines.append(f"- **Command:** `{command}`")
    lines += [
        "",
        "Every value comes from a deterministic simulation: the same arm and seed with the same "
        "questless version reproduce every row, and `runs.csv` gives the state hash to check it "
        "against. Arms share seeds, so pair rows by (seed, day) to measure what a policy changed.",
        "",
        "**Spoiler warning:** `events.csv` lists every shock, including ones a player in the run "
        "could not see coming. Don't feed it to a bot that is meant to play fairly.",
        "",
        "## What each arm changes",
        "",
    ]
    for arm in all_arms:
        if not arm.changes:
            lines.append(f"- `{arm.name}`: the scenario as written.")
        for knob, (before, after) in arm.changes.items():
            lines.append(f"- `{arm.name}`: `{knob}` {before!r} → {after!r}")
    for table, columns in COLUMNS.items():
        if table.removesuffix(".csv") not in tables:
            continue
        lines += ["", f"## {table}", "", "| Column | Meaning |", "|---|---|"]
        lines += [f"| `{col}` | {meaning} |" for col, meaning in columns.items()]
    goods = ", ".join(f"`{g}`" for g in map(str, GOODS))
    lines += ["", f"`<good>` is one of {goods}.", ""]
    return "\n".join(lines)


def _ranges(seeds: list[int]) -> str:
    if seeds and seeds == list(range(seeds[0], seeds[-1] + 1)):
        return f"{seeds[0]}-{seeds[-1]}" if len(seeds) > 1 else str(seeds[0])
    return ", ".join(map(str, seeds))
