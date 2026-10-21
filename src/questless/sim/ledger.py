# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""The ledger: single source of truth for every coin and good in the world.

Every holding (NPC wallets and inventories, guild treasuries, site stockpiles, escrow, the player,
the world outside the map) is a balance on an account here. State changes only through four
operations, each of which is journalled:

- ``open_account``: genesis balances, allowed only before the ledger is sealed.
- ``transfer``: moves an asset between accounts; totals unchanged.
- ``produce``: creates goods (never coin) from a recipe.
- ``consume``: destroys goods (never coin) through eating, wear or recipe inputs.

Conservation therefore reduces to: for every asset,
``sum(balances) == genesis + produced - consumed``, and for coin ``produced == consumed == 0``.
"""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class Asset(StrEnum):
    COIN = "coin"
    FOOD = "food"
    IRON_ORE = "iron_ore"
    TOOLS = "tools"
    WEAPONS = "weapons"


GOODS: tuple[Asset, ...] = tuple(a for a in Asset if a is not Asset.COIN)


class EntryKind(StrEnum):
    GENESIS = "genesis"
    TRANSFER = "transfer"
    PRODUCE = "produce"
    CONSUME = "consume"


@dataclass(frozen=True, slots=True)
class Entry:
    tick: int
    kind: EntryKind
    asset: Asset
    qty: int
    src: str | None
    dst: str | None
    reason: str


class LedgerError(Exception):
    """Base class for rejected ledger operations."""


class InsufficientBalance(LedgerError):
    pass


class InvalidOperation(LedgerError):
    pass


class ConservationError(AssertionError):
    pass


class Ledger:
    def __init__(self, journal_limit: int | None = 50_000) -> None:
        self._balances: dict[str, Counter[Asset]] = {}
        self._genesis: Counter[Asset] = Counter()
        self._produced: Counter[Asset] = Counter()
        self._consumed: Counter[Asset] = Counter()
        self._sealed = False
        # Bounded so long runs stay cheap; totals above are exact regardless of the limit.
        self.journal: deque[Entry] = deque(maxlen=journal_limit)

    # --- accounts -------------------------------------------------------------------------------

    def open_account(self, account: str, initial: Mapping[Asset, int] | None = None) -> None:
        if self._sealed:
            raise InvalidOperation(f"ledger sealed: cannot open {account!r} with genesis balances")
        if account in self._balances:
            raise InvalidOperation(f"account {account!r} already exists")
        balances: Counter[Asset] = Counter()
        for asset, qty in (initial or {}).items():
            asset = Asset(asset)
            _check_qty(qty)
            if qty:
                balances[asset] = qty
                self._genesis[asset] += qty
                self.journal.append(
                    Entry(0, EntryKind.GENESIS, asset, qty, None, account, "genesis")
                )
        self._balances[account] = balances

    def add_empty_account(self, account: str) -> None:
        """Open an account with no balances. Allowed after sealing (e.g. a new guild)."""
        if account in self._balances:
            raise InvalidOperation(f"account {account!r} already exists")
        self._balances[account] = Counter()

    def seal(self) -> None:
        """End genesis. From here on coin supply is fixed and goods only change via recipes."""
        self._sealed = True

    @property
    def sealed(self) -> bool:
        return self._sealed

    def accounts(self) -> list[str]:
        return sorted(self._balances)

    def has_account(self, account: str) -> bool:
        return account in self._balances

    # --- queries --------------------------------------------------------------------------------

    def balance(self, account: str, asset: Asset) -> int:
        return self._account(account)[asset]

    def holdings(self, account: str) -> dict[Asset, int]:
        return {a: q for a, q in sorted(self._account(account).items()) if q}

    def total(self, asset: Asset) -> int:
        return sum(b[asset] for b in self._balances.values())

    def totals(self) -> dict[Asset, int]:
        return {a: self.total(a) for a in Asset}

    def flows(self) -> dict[str, dict[Asset, int]]:
        return {
            "genesis": dict(self._genesis),
            "produced": dict(self._produced),
            "consumed": dict(self._consumed),
        }

    # --- operations -----------------------------------------------------------------------------

    def transfer(
        self, src: str, dst: str, asset: Asset, qty: int, *, tick: int, reason: str
    ) -> None:
        _check_qty(qty)
        if qty == 0:
            return
        if src == dst:
            raise InvalidOperation(f"transfer to self on {src!r}")
        source, target = self._account(src), self._account(dst)
        if source[asset] < qty:
            raise InsufficientBalance(
                f"{src} has {source[asset]} {asset}, needs {qty} ({reason}, tick {tick})"
            )
        source[asset] -= qty
        target[asset] += qty
        self.journal.append(Entry(tick, EntryKind.TRANSFER, asset, qty, src, dst, reason))

    def produce(self, account: str, asset: Asset, qty: int, *, tick: int, reason: str) -> None:
        _check_qty(qty)
        if asset is Asset.COIN:
            raise InvalidOperation("coin cannot be produced; supply is fixed at genesis")
        if qty == 0:
            return
        self._account(account)[asset] += qty
        self._produced[asset] += qty
        self.journal.append(Entry(tick, EntryKind.PRODUCE, asset, qty, None, account, reason))

    def consume(self, account: str, asset: Asset, qty: int, *, tick: int, reason: str) -> None:
        _check_qty(qty)
        if asset is Asset.COIN:
            raise InvalidOperation("coin cannot be destroyed; supply is fixed at genesis")
        if qty == 0:
            return
        holder = self._account(account)
        if holder[asset] < qty:
            raise InsufficientBalance(
                f"{account} has {holder[asset]} {asset}, cannot consume {qty} ({reason})"
            )
        holder[asset] -= qty
        self._consumed[asset] += qty
        self.journal.append(Entry(tick, EntryKind.CONSUME, asset, qty, account, None, reason))

    # --- invariants -----------------------------------------------------------------------------

    def check_conservation(self) -> None:
        """Raise ConservationError if any asset was created or destroyed outside the rules."""
        problems: list[str] = []
        for asset in Asset:
            expected = self._genesis[asset] + self._produced[asset] - self._consumed[asset]
            actual = self.total(asset)
            if actual != expected:
                problems.append(f"{asset}: expected {expected}, found {actual}")
        if self._produced[Asset.COIN] or self._consumed[Asset.COIN]:
            problems.append("coin supply changed after genesis")
        negatives = [
            f"{acct}:{asset}={qty}"
            for acct, bal in self._balances.items()
            for asset, qty in bal.items()
            if qty < 0
        ]
        if negatives:
            problems.append("negative balances: " + ", ".join(sorted(negatives)))
        if problems:
            raise ConservationError("; ".join(problems))

    def snapshot(self) -> dict[str, dict[str, int]]:
        """Deterministic, JSON-friendly view of all non-zero balances."""
        return {
            acct: {str(a): q for a, q in sorted(bal.items()) if q}
            for acct, bal in sorted(self._balances.items())
        }

    # --- internals ------------------------------------------------------------------------------

    def _account(self, account: str) -> Counter[Asset]:
        try:
            return self._balances[account]
        except KeyError:
            raise InvalidOperation(f"unknown account {account!r}") from None


def _check_qty(qty: int) -> None:
    if not isinstance(qty, int) or isinstance(qty, bool):
        raise InvalidOperation(f"quantities must be integers, got {qty!r}")
    if qty < 0:
        raise InvalidOperation(f"quantity must be non-negative, got {qty}")
