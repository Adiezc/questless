# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Entity data models. Holdings (coin, goods) live in the Ledger, keyed by ``account``."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum

from questless.sim.ledger import Asset

HISTORY_DAYS = 30

# Fixed system accounts.
TOWN = "town"
ESCROW = "escrow"
PLAYER = "player"
OUTSIDE = "outside"  # the world beyond the map: source of caravan imports, sink for their coin


class Profession(StrEnum):
    FARMER = "farmer"
    MINER = "miner"
    BLACKSMITH = "blacksmith"
    MERCHANT = "merchant"
    GUARD = "guard"


class Site(StrEnum):
    MARKET = "market"
    MINE = "mine"
    FARMS = "farms"


class NPCState(StrEnum):
    WORKING = "working"
    IDLE_NO_INPUT = "idle_no_input"
    HUNGRY = "hungry"
    WAITING_ON_CONTRACT = "waiting_on_contract"


def site_account(site: Site) -> str:
    """Stockpile at a production site, waiting for transport to the market."""
    return f"site:{site}"


def guild_account(guild_id: str) -> str:
    return f"guild:{guild_id}"


@dataclass(frozen=True, slots=True)
class Traits:
    skill: float  # production multiplier
    thrift: float  # 0..1, share of wallet held back as cash reserve
    stock_days: int  # days of inputs/food an NPC tries to keep on hand
    patience: int  # days a need may stay unmet before the NPC escalates it


@dataclass(slots=True)
class DailyRecord:
    tick: int
    produced: dict[Asset, int] = field(default_factory=dict)
    consumed: dict[Asset, int] = field(default_factory=dict)
    bought: dict[Asset, int] = field(default_factory=dict)
    sold: dict[Asset, int] = field(default_factory=dict)
    unmet: dict[Asset, int] = field(default_factory=dict)


@dataclass(slots=True)
class NPC:
    id: str  # also the ledger account id, e.g. "npc_042"
    name: str
    profession: Profession
    site: Site
    traits: Traits
    guild_id: str | None = None
    tool_condition: float = 1.0  # tools for workers, weapons for guards
    hunger: int = 0
    state: NPCState = NPCState.WORKING
    history: deque[DailyRecord] = field(default_factory=lambda: deque(maxlen=HISTORY_DAYS))

    @property
    def account(self) -> str:
        return self.id


@dataclass(frozen=True, slots=True)
class GuildPolicy:
    emergency_threshold: float  # share of members sharing a need that triggers a guild contract
    max_contract_share: float  # max share of treasury one contract may escrow
    reward_premium: float  # multiplier over market value for guild-funded contracts


@dataclass(slots=True)
class Guild:
    id: str
    name: str
    policy: GuildPolicy
    dues_rate: float
    members: list[str] = field(default_factory=list)  # NPC ids, sorted
    reputation: dict[str, int] = field(default_factory=dict)  # player id -> -100..100
    rival: str | None = None

    @property
    def account(self) -> str:
        return guild_account(self.id)
