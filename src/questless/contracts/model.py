# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Contract data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from questless.contracts.provenance import Provenance
from questless.sim.ledger import Asset


class ContractKind(StrEnum):
    PROCUREMENT = "procurement"  # an NPC needs goods delivered
    GUILD_SUPPLY = "guild_supply"  # a guild pools members' needs into one contract
    TOWN_SUPPLY = "town_supply"  # the town pools its guards' needs into one contract
    TRANSPORT = "transport"  # goods stuck at production sites must be hauled to market
    RELIEF = "relief"  # relief aid for poverty-trapped NPCs funded by guild or town
    ENFORCEMENT = "enforcement"  # town-funded contract to intercept smuggling runs (M19.4)
    SMUGGLING_RUN = "smuggling_run"  # smuggler-funded contract to carry contraband (M19.4)


class Status(StrEnum):
    OPEN = "open"
    ACCEPTED = "accepted"
    FULFILLED = "fulfilled"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


LIVE = (Status.OPEN, Status.ACCEPTED)


@dataclass(slots=True)
class Contract:
    id: str  # "C-0007", sequential
    kind: ContractKind
    requester: str  # account the contract is for: npc id, "guild:<id>" or "town"
    funder: str  # account whose coin is in escrow
    good: Asset
    qty: int
    # Who receives the goods: {npc_id: qty}. For transport, whose goods get hauled.
    beneficiaries: dict[str, int]
    reward: int  # coin held in escrow while live
    rep_reward: int
    created_tick: int
    deadline_tick: int
    dedup_key: tuple[str, str, str]  # (requester, kind, good)
    provenance: Provenance
    reason: str  # one line rendered from provenance
    status: Status = Status.OPEN
    accepted_by: str | None = None
    closed_tick: int | None = None
    parent_id: str | None = None
    outcome: dict = field(default_factory=dict)  # filled in after resolution (M6/M7)

    @property
    def live(self) -> bool:
        return self.status in LIVE
