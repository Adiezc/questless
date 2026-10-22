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

    def settle_tick(
        self,
        tick: int,
        ledger: Ledger,
        spot_prices: dict[str, int],
    ) -> list[dict[str, Any]]:
        """Settle all futures positions due on `tick`.

        Physical delivery rules:
        - If seller has >= future.qty in goods:
          1. Deliver `future.qty` goods from seller to buyer.
          2. Transfer buyer escrow (`future.notional` coin) to seller.
          3. Return seller collateral (`future.collateral` coin) to seller.
          4. Settle delivery obligation in registry.
          5. Mark future SETTLED.
        - If seller cannot deliver (seller goods < future.qty):
          1. Refund buyer escrow (`future.notional` coin) to buyer.
          2. Spot compensation = max(spot - strike, 0) * qty.
             Buyer receives compensation up to available collateral.
          3. Any remaining collateral is returned to seller.
          4. If collateral was insufficient or seller defaulted, mark obligation DEFAULTED.
          5. Mark future DEFAULTED.
        """
        results: list[dict[str, Any]] = []
        due = [
            f
            for f in self.positions.values()
            if f.status == FutureStatus.OPEN and f.delivery_tick == tick
        ]

        for f in due:
            seller_goods = ledger.balance(f.seller, f.good)
            spot = spot_prices.get(f.good, f.strike)

            if seller_goods >= f.qty:
                # 1. Physical delivery of goods
                ledger.transfer(
                    f.seller,
                    f.buyer,
                    f.good,
                    f.qty,
                    tick=tick,
                    reason="future_physical_delivery",
                )
                # 2. Release buyer escrow to seller
                ledger.transfer(
                    f.buyer_escrow_account,
                    f.seller,
                    "coin",
                    f.notional,
                    tick=tick,
                    reason="future_escrow_release",
                )
                # 3. Return seller collateral to seller
                ledger.transfer(
                    f.seller_collateral_account,
                    f.seller,
                    "coin",
                    f.collateral,
                    tick=tick,
                    reason="future_collateral_return",
                )
                # 4. Settle obligation
                self.registry.settle(f.delivery_obligation_id, f.notional)
                f.status = FutureStatus.SETTLED

                results.append(
                    {
                        "future_id": f.id,
                        "status": "settled",
                        "delivered_qty": f.qty,
                        "escrow_paid": f.notional,
                        "collateral_returned": f.collateral,
                    }
                )
            else:
                # Default path
                # 1. Refund buyer escrow in full
                ledger.transfer(
                    f.buyer_escrow_account,
                    f.buyer,
                    "coin",
                    f.notional,
                    tick=tick,
                    reason="future_default_escrow_refund",
                )

                # 2. Compensation from collateral: max(spot - strike, 0) * qty
                comp_due = max(0, spot - f.strike) * f.qty
                collateral_avail = ledger.balance(f.seller_collateral_account, "coin")
                comp_paid = min(comp_due, collateral_avail)

                if comp_paid > 0:
                    ledger.transfer(
                        f.seller_collateral_account,
                        f.buyer,
                        "coin",
                        comp_paid,
                        tick=tick,
                        reason="future_default_compensation",
                    )

                # 3. Return remainder of collateral to seller
                rem_collateral = ledger.balance(f.seller_collateral_account, "coin")
                if rem_collateral > 0:
                    ledger.transfer(
                        f.seller_collateral_account,
                        f.seller,
                        "coin",
                        rem_collateral,
                        tick=tick,
                        reason="future_default_collateral_return",
                    )

                # 4. Record default in M17 obligation registry
                self.registry.default(f.delivery_obligation_id)
                f.status = FutureStatus.DEFAULTED

                results.append(
                    {
                        "future_id": f.id,
                        "status": "defaulted",
                        "spot": spot,
                        "strike": f.strike,
                        "compensation_due": comp_due,
                        "compensation_paid": comp_paid,
                    }
                )

        return results

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
