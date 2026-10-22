"""Obligation registry for Questless loans and contracts (M17.1).

Defines:
- ``ObligationStatus``: Lifecycle of an obligation (ACTIVE, SETTLED, DEFAULTED).
- ``Obligation``: Core contract backed by escrow to preserve coin conservation.
- ``ObligationRegistry``: Manages opening, query by due date, settlement, and default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class ObligationStatus(Enum):
    ACTIVE = auto()
    SETTLED = auto()
    DEFAULTED = auto()


@dataclass
class Obligation:
    id: str
    debtor: str
    creditor: str
    principal: int
    rate: float
    schedule: list[int]  # tick days on which instalments fall due
    collateral_account: str
    status: ObligationStatus = ObligationStatus.ACTIVE
    paid: int = 0
    created_tick: int = 0

    def total_due(self) -> int:
        """Total repayment amount including interest."""
        return int(round(self.principal * (1.0 + self.rate)))

    def remaining_due(self) -> int:
        return max(0, self.total_due() - self.paid)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "debtor": self.debtor,
            "creditor": self.creditor,
            "principal": self.principal,
            "rate": self.rate,
            "schedule": list(self.schedule),
            "collateral_account": self.collateral_account,
            "status": self.status.name,
            "paid": self.paid,
            "created_tick": self.created_tick,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Obligation:
        return cls(
            id=data["id"],
            debtor=data["debtor"],
            creditor=data["creditor"],
            principal=data["principal"],
            rate=data["rate"],
            schedule=list(data["schedule"]),
            collateral_account=data["collateral_account"],
            status=ObligationStatus[data["status"]],
            paid=data.get("paid", 0),
            created_tick=data.get("created_tick", 0),
        )


@dataclass
class ObligationRegistry:
    obligations: dict[str, Obligation] = field(default_factory=dict)
    next_id: int = 1

    def open(
        self,
        debtor: str,
        creditor: str,
        principal: int,
        rate: float,
        schedule: list[int],
        collateral_account: str,
        tick: int = 0,
    ) -> Obligation:
        """Register a new financial obligation."""
        ob_id = f"OB-{self.next_id}"
        self.next_id += 1
        ob = Obligation(
            id=ob_id,
            debtor=debtor,
            creditor=creditor,
            principal=principal,
            rate=rate,
            schedule=schedule,
            collateral_account=collateral_account,
            created_tick=tick,
        )
        self.obligations[ob_id] = ob
        return ob

    def due_today(self, tick: int) -> list[Obligation]:
        """Return active obligations with payments scheduled for today."""
        return [
            ob
            for ob in self.obligations.values()
            if ob.status == ObligationStatus.ACTIVE and tick in ob.schedule
        ]

    def settle(self, obligation_id: str, amount: int | None = None) -> Obligation:
        """Record payment toward an obligation, marking SETTLED if paid in full."""
        if obligation_id not in self.obligations:
            raise KeyError(f"Unknown obligation '{obligation_id}'")
        ob = self.obligations[obligation_id]
        if ob.status != ObligationStatus.ACTIVE:
            return ob

        amt = amount if amount is not None else ob.remaining_due()
        ob.paid += amt
        if ob.paid >= ob.total_due():
            ob.status = ObligationStatus.SETTLED
        return ob

    def default(self, obligation_id: str) -> Obligation:
        """Mark an obligation as DEFAULTED."""
        if obligation_id not in self.obligations:
            raise KeyError(f"Unknown obligation '{obligation_id}'")
        ob = self.obligations[obligation_id]
        if ob.status == ObligationStatus.ACTIVE:
            ob.status = ObligationStatus.DEFAULTED
        return ob

    def to_dict(self) -> dict[str, Any]:
        return {
            "next_id": self.next_id,
            "obligations": {k: v.to_dict() for k, v in self.obligations.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ObligationRegistry:
        reg = cls(next_id=data.get("next_id", 1))
        for k, v in data.get("obligations", {}).items():
            reg.obligations[k] = Obligation.from_dict(v)
        return reg
