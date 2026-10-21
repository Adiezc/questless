# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Scenario configuration: TOML file -> validated, typed, immutable config.

Every tuning value lives in ``scenarios/*.toml``. Unknown keys are rejected so a typo in a scenario
fails loudly instead of silently falling back to a default.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from questless.sim.entities import GuildPolicy, Profession, Site
from questless.sim.ledger import GOODS, Asset


class ConfigError(ValueError):
    pass


IntRange = tuple[int, int]
FloatRange = tuple[float, float]


@dataclass(frozen=True)
class GoodConfig:
    base_price: int
    price_floor: float  # multiple of base_price
    price_ceiling: float


@dataclass(frozen=True)
class ProfessionConfig:
    count: int
    site: Site
    wallet: IntRange
    inventory: Mapping[Asset, int]
    tool_condition: FloatRange
    equipment: Asset | None  # good that wears out and must be replaced (tools / weapons)
    wear: float  # equipment condition lost per working day
    no_tool_factor: float  # productivity multiplier while equipment is broken
    output: Mapping[Asset, float]  # gatherers: base units per day
    crafts_per_day: int  # crafters: base crafts per day
    recipes: Mapping[Asset, Mapping[Asset, int]]  # crafted good -> inputs for one unit


@dataclass(frozen=True)
class NeedsConfig:
    food_per_day: int
    equipment_threshold: float  # replace equipment when condition drops below this
    hungry_after: int  # days without food before productivity drops
    hungry_productivity: float
    max_unsold_days: int  # producers pause once this many days of output sit unsold


class ShockEffect(StrEnum):
    SITE_OUTPUT = "site_output"
    TRANSPORT_CAPACITY = "transport_capacity"


@dataclass(frozen=True)
class ShockConfig:
    name: str
    effect: ShockEffect
    start: int
    duration: int
    factor: float
    site: Site | None = None


@dataclass(frozen=True)
class TraitRanges:
    skill: FloatRange
    thrift: FloatRange
    stock_days: IntRange
    patience: IntRange


@dataclass(frozen=True)
class GuildConfig:
    name: str
    professions: tuple[Profession, ...]
    treasury: int
    dues_rate: float
    policy: GuildPolicy


@dataclass(frozen=True)
class MarketConfig:
    price_adjustment: float  # max daily relative price change (alpha)
    target_cover_days: float  # stock-to-demand ratio at which prices hold steady
    stock_weight: float  # weight of the stock (cover) term vs the flow term in price changes
    effort: FloatRange  # gatherer effort multiplier range, driven by price / base price


@dataclass(frozen=True)
class TransportConfig:
    capacity_per_merchant: int  # units per day moved from production sites to the market
    fee_rate: float  # share of the goods' market value the producer pays the carriers


@dataclass(frozen=True)
class ContractsConfig:
    max_open: int  # global cap on OPEN + ACCEPTED contracts
    max_new_per_tick: int
    deadline_days: int
    cooldown_days: int  # no new contract for the same key after one closes unfulfilled
    resolve_days: int  # an OPEN contract is cancelled once its need is gone this many days
    npc_premium: float  # reward multiplier over market value for contracts NPCs fund
    urgency_step: float  # extra premium per day the need persists beyond patience
    max_urgency: float
    town_max_share: float  # most of the town treasury one contract may escrow
    caravan_days: int  # days an import from outside takes; deadlines must allow for it
    transport_backlog_days: float  # site backlog, in days of output, that signals a bottleneck
    min_reward: int  # contracts worth less than this are not posted (board clutter)
    town_emergency_threshold: float  # share of guards short of a good that triggers town supply


@dataclass(frozen=True)
class TownConfig:
    treasury: int
    guard_wage: int
    market_tax: float
    upkeep_rate: float  # daily levy on NPC coin above upkeep_exempt; recycles idle coin
    upkeep_exempt: int


@dataclass(frozen=True)
class ScenarioConfig:
    name: str
    description: str
    seed: int
    days: int
    guilds_enabled: bool
    goods: Mapping[Asset, GoodConfig]
    professions: Mapping[Profession, ProfessionConfig]
    traits: TraitRanges
    needs: NeedsConfig
    market: MarketConfig
    transport: TransportConfig
    contracts: ContractsConfig
    guilds: Mapping[str, GuildConfig]
    town: TownConfig
    player_wallet: int
    outside: Mapping[Asset, int]
    shocks: tuple[ShockConfig, ...] = ()

    @property
    def population(self) -> int:
        return sum(p.count for p in self.professions.values())


# --- loading -------------------------------------------------------------------------------------


def load_scenario(path: str | Path) -> ScenarioConfig:
    path = Path(path)
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: invalid TOML: {exc}") from exc
    return parse_scenario(data, source=str(path))


def parse_scenario(data: Mapping[str, Any], source: str = "<scenario>") -> ScenarioConfig:
    try:
        return _parse(data)
    except ConfigError as exc:
        raise ConfigError(f"{source}: {exc}") from None


def _parse(data: Mapping[str, Any]) -> ScenarioConfig:
    _keys(
        data,
        "scenario",
        required={
            "scenario",
            "goods",
            "professions",
            "traits",
            "needs",
            "market",
            "transport",
            "contracts",
            "guilds",
            "town",
            "player",
        },
        optional={"outside", "shocks"},
    )

    sc = data["scenario"]
    _keys(sc, "scenario", required={"name", "seed", "days"}, optional={"description", "guilds"})

    goods = {}
    _keys(data["goods"], "goods", required={str(g) for g in GOODS})
    for name, g in data["goods"].items():
        _keys(g, f"goods.{name}", required={"base_price", "price_floor", "price_ceiling"})
        floor, ceiling = float(g["price_floor"]), float(g["price_ceiling"])
        if not 0 < floor <= 1 <= ceiling:
            raise ConfigError(f"goods.{name}: need 0 < price_floor <= 1 <= price_ceiling")
        goods[Asset(name)] = GoodConfig(_pos_int(g["base_price"], f"goods.{name}"), floor, ceiling)

    professions = {}
    _keys(data["professions"], "professions", required={str(p) for p in Profession})
    for name, p in data["professions"].items():
        where = f"professions.{name}"
        _keys(
            p,
            where,
            required={"count", "site", "wallet", "tool_condition"},
            optional={
                "inventory",
                "equipment",
                "wear",
                "no_tool_factor",
                "output",
                "crafts_per_day",
                "recipes",
            },
        )
        equipment = p.get("equipment")
        output = p.get("output", {})
        recipes = p.get("recipes", {})
        if not isinstance(output, Mapping) or not isinstance(recipes, Mapping):
            raise ConfigError(f"{where}: output and recipes must be tables")
        professions[Profession(name)] = ProfessionConfig(
            count=_nonneg_int(p["count"], f"{where}.count"),
            site=_enum(Site, p["site"], f"{where}.site"),
            wallet=_int_range(p["wallet"], f"{where}.wallet"),
            inventory=_holdings(p.get("inventory", {}), f"{where}.inventory"),
            tool_condition=_float_range(p["tool_condition"], f"{where}.tool_condition", 0, 1),
            equipment=None if equipment is None else _good(equipment, f"{where}.equipment"),
            wear=_fraction(p.get("wear", 0.0), f"{where}.wear"),
            no_tool_factor=_fraction(p.get("no_tool_factor", 1.0), f"{where}.no_tool_factor"),
            output={
                _good(g, f"{where}.output"): _at_least(q, 0.0, f"{where}.output.{g}")
                for g, q in output.items()
            },
            crafts_per_day=_nonneg_int(p.get("crafts_per_day", 0), f"{where}.crafts_per_day"),
            recipes={
                _good(g, f"{where}.recipes"): _holdings(inputs, f"{where}.recipes.{g}")
                for g, inputs in recipes.items()
            },
        )
        if professions[Profession(name)].crafts_per_day and not recipes:
            raise ConfigError(f"{where}: crafts_per_day set but no recipes")

    t = data["traits"]
    _keys(t, "traits", required={"skill", "thrift", "stock_days", "patience"})
    traits = TraitRanges(
        skill=_float_range(t["skill"], "traits.skill", 0.01, 10),
        thrift=_float_range(t["thrift"], "traits.thrift", 0, 1),
        stock_days=_int_range(t["stock_days"], "traits.stock_days", 1),
        patience=_int_range(t["patience"], "traits.patience", 1),
    )

    n = data["needs"]
    _keys(
        n,
        "needs",
        required={
            "food_per_day",
            "equipment_threshold",
            "hungry_after",
            "hungry_productivity",
            "max_unsold_days",
        },
    )
    needs = NeedsConfig(
        food_per_day=_nonneg_int(n["food_per_day"], "needs.food_per_day"),
        equipment_threshold=_fraction(n["equipment_threshold"], "needs.equipment_threshold"),
        hungry_after=_nonneg_int(n["hungry_after"], "needs.hungry_after"),
        hungry_productivity=_fraction(n["hungry_productivity"], "needs.hungry_productivity"),
        max_unsold_days=_pos_int(n["max_unsold_days"], "needs.max_unsold_days"),
    )

    m = data["market"]
    _keys(
        m,
        "market",
        required={"price_adjustment", "target_cover_days", "stock_weight", "effort"},
    )
    market = MarketConfig(
        price_adjustment=_fraction(m["price_adjustment"], "market.price_adjustment"),
        target_cover_days=_at_least(m["target_cover_days"], 0.1, "market.target_cover_days"),
        stock_weight=_fraction(m["stock_weight"], "market.stock_weight"),
        effort=_float_range(m["effort"], "market.effort", 0.0, 5.0),
    )
    tr = data["transport"]
    _keys(tr, "transport", required={"capacity_per_merchant", "fee_rate"})
    transport = TransportConfig(
        capacity_per_merchant=_nonneg_int(tr["capacity_per_merchant"], "transport"),
        fee_rate=_fraction(tr["fee_rate"], "transport.fee_rate"),
    )

    c = data["contracts"]
    fields = {
        "max_open": _pos_int,
        "max_new_per_tick": _pos_int,
        "deadline_days": _pos_int,
        "cooldown_days": _nonneg_int,
        "resolve_days": _pos_int,
        "caravan_days": _nonneg_int,
        "min_reward": _pos_int,
    }
    floats = {
        "npc_premium": 1.0,
        "urgency_step": 0.0,
        "max_urgency": 1.0,
        "town_max_share": 0.0,
        "transport_backlog_days": 0.0,
        "town_emergency_threshold": 0.0,
    }
    _keys(c, "contracts", required=set(fields) | set(floats))
    contracts = ContractsConfig(
        **{k: f(c[k], f"contracts.{k}") for k, f in fields.items()},
        **{k: _at_least(c[k], lo, f"contracts.{k}") for k, lo in floats.items()},
    )
    if contracts.town_max_share > 1:
        raise ConfigError("contracts.town_max_share: must be between 0 and 1")

    shocks = []
    for i, sh in enumerate(data.get("shocks", [])):
        where = f"shocks[{i}]"
        _keys(
            sh, where, required={"name", "effect", "start", "duration", "factor"}, optional={"site"}
        )
        shock = ShockConfig(
            name=str(sh["name"]),
            effect=_enum(ShockEffect, sh["effect"], f"{where}.effect"),
            start=_nonneg_int(sh["start"], f"{where}.start"),
            duration=_pos_int(sh["duration"], f"{where}.duration"),
            factor=_at_least(sh["factor"], 0.0, f"{where}.factor"),
            site=None if "site" not in sh else _enum(Site, sh["site"], f"{where}.site"),
        )
        if shock.effect is ShockEffect.SITE_OUTPUT and shock.site is None:
            raise ConfigError(f"{where}: site_output shocks need a site")
        shocks.append(shock)

    guilds = {}
    claimed: dict[Profession, str] = {}
    for gid, g in data["guilds"].items():
        where = f"guilds.{gid}"
        _keys(g, where, required={"name", "professions", "treasury", "dues_rate", "policy"})
        profs = tuple(_enum(Profession, p, f"{where}.professions") for p in g["professions"])
        for prof in profs:
            if prof in claimed:
                raise ConfigError(f"{where}: {prof} already belongs to guild {claimed[prof]!r}")
            claimed[prof] = gid
        pol = g["policy"]
        _keys(
            pol,
            f"{where}.policy",
            required={
                "emergency_threshold",
                "max_contract_share",
                "reward_premium",
                "relief_days",
                "max_daily_relief_share",
                "reserve",
            },
        )
        guilds[gid] = GuildConfig(
            name=str(g["name"]),
            professions=profs,
            treasury=_nonneg_int(g["treasury"], f"{where}.treasury"),
            dues_rate=_fraction(g["dues_rate"], f"{where}.dues_rate"),
            policy=GuildPolicy(
                emergency_threshold=_fraction(pol["emergency_threshold"], f"{where}.policy"),
                max_contract_share=_fraction(pol["max_contract_share"], f"{where}.policy"),
                reward_premium=_at_least(pol["reward_premium"], 1.0, f"{where}.policy"),
                relief_days=_nonneg_int(pol["relief_days"], f"{where}.policy.relief_days"),
                max_daily_relief_share=_fraction(
                    pol["max_daily_relief_share"], f"{where}.policy.max_daily_relief_share"
                ),
                reserve=_nonneg_int(pol["reserve"], f"{where}.policy.reserve"),
            ),
        )

    town = data["town"]
    _keys(
        town,
        "town",
        required={"treasury", "guard_wage", "market_tax", "upkeep_rate", "upkeep_exempt"},
    )
    player = data["player"]
    _keys(player, "player", required={"wallet"})

    cfg = ScenarioConfig(
        name=str(sc["name"]),
        description=str(sc.get("description", "")),
        seed=_nonneg_int(sc["seed"], "scenario.seed"),
        days=_pos_int(sc["days"], "scenario.days"),
        guilds_enabled=bool(sc.get("guilds", True)),
        goods=goods,
        professions=professions,
        traits=traits,
        needs=needs,
        market=market,
        transport=transport,
        contracts=contracts,
        guilds=guilds,
        town=TownConfig(
            treasury=_nonneg_int(town["treasury"], "town.treasury"),
            guard_wage=_nonneg_int(town["guard_wage"], "town.guard_wage"),
            market_tax=_fraction(town["market_tax"], "town.market_tax"),
            upkeep_rate=_fraction(town["upkeep_rate"], "town.upkeep_rate"),
            upkeep_exempt=_nonneg_int(town["upkeep_exempt"], "town.upkeep_exempt"),
        ),
        player_wallet=_nonneg_int(player["wallet"], "player.wallet"),
        outside=_holdings(data.get("outside", {}), "outside"),
        shocks=tuple(shocks),
    )
    if cfg.population <= 0:
        raise ConfigError("population is zero")
    if cfg.population > 1000:
        raise ConfigError(f"population {cfg.population} exceeds prototype limit of 1000")
    return cfg


# --- validators ----------------------------------------------------------------------------------


def _keys(
    table: Any, where: str, *, required: set[str], optional: frozenset[str] | set[str] = frozenset()
) -> None:
    if not isinstance(table, Mapping):
        raise ConfigError(f"{where}: expected a table")
    missing = required - table.keys()
    unknown = table.keys() - required - optional
    if missing:
        raise ConfigError(f"{where}: missing {sorted(missing)}")
    if unknown:
        raise ConfigError(f"{where}: unknown keys {sorted(unknown)}")


def _enum(enum: type, value: Any, where: str) -> Any:
    try:
        return enum(value)
    except ValueError:
        options = ", ".join(e.value for e in enum)
        raise ConfigError(f"{where}: {value!r} is not one of: {options}") from None


def _good(value: Any, where: str) -> Asset:
    asset = _enum(Asset, value, where)
    if asset is Asset.COIN:
        raise ConfigError(f"{where}: coin is not a good")
    return asset


def _int(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(f"{where}: expected an integer, got {value!r}")
    return value


def _nonneg_int(value: Any, where: str) -> int:
    v = _int(value, where)
    if v < 0:
        raise ConfigError(f"{where}: must be >= 0")
    return v


def _pos_int(value: Any, where: str) -> int:
    v = _int(value, where)
    if v <= 0:
        raise ConfigError(f"{where}: must be > 0")
    return v


def _number(value: Any, where: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ConfigError(f"{where}: expected a number, got {value!r}")
    return float(value)


def _fraction(value: Any, where: str) -> float:
    v = _number(value, where)
    if not 0 <= v <= 1:
        raise ConfigError(f"{where}: must be between 0 and 1")
    return v


def _at_least(value: Any, minimum: float, where: str) -> float:
    v = _number(value, where)
    if v < minimum:
        raise ConfigError(f"{where}: must be >= {minimum}")
    return v


def _pair(value: Any, where: str) -> tuple[Any, Any]:
    if not isinstance(value, list | tuple) or len(value) != 2:
        raise ConfigError(f"{where}: expected [low, high]")
    return value[0], value[1]


def _int_range(value: Any, where: str, minimum: int = 0) -> IntRange:
    lo, hi = (_int(v, where) for v in _pair(value, where))
    if not minimum <= lo <= hi:
        raise ConfigError(f"{where}: need {minimum} <= low <= high, got [{lo}, {hi}]")
    return lo, hi


def _float_range(value: Any, where: str, minimum: float, maximum: float) -> FloatRange:
    lo, hi = (_number(v, where) for v in _pair(value, where))
    if not minimum <= lo <= hi <= maximum:
        raise ConfigError(f"{where}: need {minimum} <= low <= high <= {maximum}")
    return lo, hi


def _holdings(table: Any, where: str) -> dict[Asset, int]:
    if not isinstance(table, Mapping):
        raise ConfigError(f"{where}: expected a table")
    out: dict[Asset, int] = {}
    for name, qty in table.items():
        asset = _enum(Asset, name, where)
        if asset is Asset.COIN:
            raise ConfigError(f"{where}: coin is set via wallet/treasury, not inventory")
        out[asset] = _nonneg_int(qty, f"{where}.{name}")
    return out
