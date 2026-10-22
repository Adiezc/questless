"""Futures contract dataclass and escrow operations (M18.1).

Defines:
- ``Future``: Physically settled forward commitment on goods.
- ``FuturesMarket``: Handles escrowing of buyer notional and seller collateral.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

from questless.finance.obligations import ObligationRegistry

if TYPE_CHECKING:
    from questless.sim.ledger import Ledger


class FutureStatus(Enum):
    OPEN = auto()
    SETTLED = auto()
    DEFAULTED = auto()
    CANCELLED = auto()


@dataclass
class Future:
    """Physically settled futures contract (M18.1).

    - Buyer escrows: ``qty * strike`` in full.
    - Seller posts collateral: ``int(round(0.30 * qty * strike))`` (30% of notional).
    """

    id: str
    good: str
    qty: int
    strike: int
    delivery_tick: int
    buyer: str
    seller: str
    buyer_escrow_account: str
    seller_collateral_account: str
    delivery_obligation_id: str
    status: FutureStatus = FutureStatus.OPEN
    created_tick: int = 0

    @property
    def notional(self) -> int:
        return self.qty * self.strike

    @property
    def collateral(self) -> int:
        return int(round(0.30 * self.notional))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "good": self.good,
            "qty": self.qty,
            "strike": self.strike,
            "delivery_tick": self.delivery_tick,
            "buyer": self.buyer,
            "seller": self.seller,
            "buyer_escrow_account": self.buyer_escrow_account,
            "seller_collateral_account": self.seller_collateral_account,
            "delivery_obligation_id": self.delivery_obligation_id,
            "status": self.status.name,
            "created_tick": self.created_tick,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Future:
        return cls(
            id=data["id"],
            good=data["good"],
            qty=data["qty"],
            strike=data["strike"],
            delivery_tick=data["delivery_tick"],
            buyer=data["buyer"],
            seller=data["seller"],
            buyer_escrow_account=data["buyer_escrow_account"],
            seller_collateral_account=data["seller_collateral_account"],
            delivery_obligation_id=data["delivery_obligation_id"],
            status=FutureStatus[data["status"]],
            created_tick=data.get("created_tick", 0),
        )


class FuturesMarket:
    """Manages the creation, escrow, and storage of open futures positions."""

    def __init__(self, registry: ObligationRegistry | None = None) -> None:
        self.registry = registry if registry is not None else ObligationRegistry()
        self.positions: dict[str, Future] = {}
        self.next_id: int = 1

    def open_future(
        self,
        ledger: Ledger,
        good: str,
        qty: int,
        strike: int,
        delivery_tick: int,
        buyer: str,
        seller: str,
        tick: int = 0,
    ) -> Future:
        """Open a new Future, transferring buyer notional and seller collateral into escrow."""
        if qty <= 0:
            raise ValueError(f"Quantity must be positive, got {qty}")
        if strike <= 0:
            raise ValueError(f"Strike must be positive, got {strike}")

        fid = f"FUT-{self.next_id}"
        self.next_id += 1

        buyer_escrow = f"escrow:future:buyer:{fid}"
        seller_collateral = f"escrow:future:seller:{fid}"

        notional = qty * strike
        collateral = int(round(0.30 * notional))

        # Check balances
        buyer_bal = ledger.balance(buyer, "coin")
        if buyer_bal < notional:
            raise ValueError(
                f"Buyer '{buyer}' has insufficient coin ({buyer_bal}) for notional {notional}"
            )
        seller_bal = ledger.balance(seller, "coin")
        if seller_bal < collateral:
            raise ValueError(
                f"Seller '{seller}' has insufficient coin ({seller_bal}) "
                f"for collateral {collateral}"
            )

        # Transfer to escrow accounts (open escrow accounts if needed)
        existing = ledger.accounts()
        if buyer_escrow not in existing:
            ledger.open_account(buyer_escrow)
        if seller_collateral not in existing:
            ledger.open_account(seller_collateral)

        ledger.transfer(buyer, buyer_escrow, "coin", notional, tick=tick, reason="future_escrow")
        ledger.transfer(
            seller,
            seller_collateral,
            "coin",
            collateral,
            tick=tick,
            reason="future_collateral",
        )

        # Register seller delivery obligation via M17 registry
        ob = self.registry.open(
            debtor=seller,
            creditor=buyer,
            principal=notional,
            rate=0.0,
            schedule=[delivery_tick],
            collateral_account=seller_collateral,
            tick=tick,
        )

        future = Future(
            id=fid,
            good=good,
            qty=qty,
            strike=strike,
            delivery_tick=delivery_tick,
            buyer=buyer,
            seller=seller,
            buyer_escrow_account=buyer_escrow,
            seller_collateral_account=seller_collateral,
            delivery_obligation_id=ob.id,
            status=FutureStatus.OPEN,
            created_tick=tick,
        )
        self.positions[fid] = future
        return future

    def open_notional(self) -> int:
        return sum(f.notional for f in self.positions.values() if f.status == FutureStatus.OPEN)

    def total_collateral(self) -> int:
        return sum(f.collateral for f in self.positions.values() if f.status == FutureStatus.OPEN)

    def total_escrow(self) -> int:
        return self.open_notional() + self.total_collateral()

    def to_dict(self) -> dict[str, Any]:
        return {
            "next_id": self.next_id,
            "positions": {k: v.to_dict() for k, v in self.positions.items()},
            "registry": self.registry.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FuturesMarket:
        reg = ObligationRegistry.from_dict(data.get("registry", {}))
        market = cls(registry=reg)
        market.next_id = data.get("next_id", 1)
        for k, v in data.get("positions", {}).items():
            market.positions[k] = Future.from_dict(v)
        return market
