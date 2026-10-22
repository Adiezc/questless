"""Tests for M20.1 Mint and Burn in the Ledger."""

import pytest

from questless.sim.entities import CENTRAL_BANK, Asset
from questless.sim.ledger import (
    EntryKind,
    InsufficientBalance,
    InvalidOperation,
    Ledger,
)


def test_mint_and_burn_lifecycle():
    ledger = Ledger()
    ledger.open_account("town", {Asset.COIN: 1000, Asset.FOOD: 50})
    ledger.open_account(CENTRAL_BANK, {Asset.COIN: 0})
    ledger.seal()

    assert ledger.total(Asset.COIN) == 1000
    ledger.check_conservation()

    # Mint coin to central bank
    ledger.mint(CENTRAL_BANK, 250, tick=1, reason="quantitative_easing")
    assert ledger.balance(CENTRAL_BANK, Asset.COIN) == 250
    assert ledger.total(Asset.COIN) == 1250
    assert ledger.flows()["minted"] == 250
    ledger.check_conservation()

    # Burn coin from central bank
    ledger.burn(CENTRAL_BANK, 100, tick=2, reason="monetary_contraction")
    assert ledger.balance(CENTRAL_BANK, Asset.COIN) == 150
    assert ledger.total(Asset.COIN) == 1150
    assert ledger.flows()["burned"] == 100
    ledger.check_conservation()

    # Check journal records
    mint_entry = [e for e in ledger.journal if e.kind == EntryKind.MINT][0]
    assert mint_entry.dst == CENTRAL_BANK
    assert mint_entry.qty == 250

    burn_entry = [e for e in ledger.journal if e.kind == EntryKind.BURN][0]
    assert burn_entry.src == CENTRAL_BANK
    assert burn_entry.qty == 100


def test_mint_burn_guards():
    ledger = Ledger()
    ledger.open_account("town", {Asset.COIN: 500})
    ledger.open_account(CENTRAL_BANK, {Asset.COIN: 50})
    ledger.seal()

    # Non-central bank accounts cannot mint
    with pytest.raises(InvalidOperation, match="minting only allowed for central_bank"):
        ledger.mint("town", 100, tick=1, reason="illegal_mint")

    # Non-central bank accounts cannot burn
    with pytest.raises(InvalidOperation, match="burning only allowed for central_bank"):
        ledger.burn("town", 100, tick=1, reason="illegal_burn")

    # Cannot burn more than balance
    with pytest.raises(InsufficientBalance):
        ledger.burn(CENTRAL_BANK, 1000, tick=1, reason="overburn")

    # Cannot produce or consume coin
    with pytest.raises(InvalidOperation, match="coin cannot be produced"):
        ledger.produce(CENTRAL_BANK, Asset.COIN, 100, tick=1, reason="produce_coin")

    with pytest.raises(InvalidOperation, match="coin cannot be destroyed"):
        ledger.consume(CENTRAL_BANK, Asset.COIN, 10, tick=1, reason="consume_coin")
