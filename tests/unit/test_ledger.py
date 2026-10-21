# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
import pytest

from questless.sim.ledger import (
    Asset,
    ConservationError,
    InsufficientBalance,
    InvalidOperation,
    Ledger,
)


@pytest.fixture
def ledger() -> Ledger:
    led = Ledger()
    led.open_account("a", {Asset.COIN: 100, Asset.FOOD: 10})
    led.open_account("b", {Asset.COIN: 50})
    led.seal()
    return led


def test_transfer_moves_value_and_keeps_totals(ledger):
    ledger.transfer("a", "b", Asset.COIN, 30, tick=1, reason="test")
    assert ledger.balance("a", Asset.COIN) == 70
    assert ledger.balance("b", Asset.COIN) == 80
    assert ledger.total(Asset.COIN) == 150
    ledger.check_conservation()


def test_overdraft_is_rejected_and_changes_nothing(ledger):
    before = ledger.snapshot()
    with pytest.raises(InsufficientBalance):
        ledger.transfer("b", "a", Asset.COIN, 51, tick=1, reason="test")
    with pytest.raises(InsufficientBalance):
        ledger.consume("a", Asset.FOOD, 11, tick=1, reason="test")
    assert ledger.snapshot() == before


@pytest.mark.parametrize("qty", [-1, 1.5, True])
def test_non_integer_or_negative_quantities_are_rejected(ledger, qty):
    with pytest.raises(InvalidOperation):
        ledger.transfer("a", "b", Asset.COIN, qty, tick=1, reason="test")


def test_coin_supply_is_fixed_after_genesis(ledger):
    with pytest.raises(InvalidOperation):
        ledger.produce("a", Asset.COIN, 1, tick=1, reason="mint")
    with pytest.raises(InvalidOperation):
        ledger.consume("a", Asset.COIN, 1, tick=1, reason="burn")
    with pytest.raises(InvalidOperation):
        ledger.open_account("c", {Asset.COIN: 1})


def test_produce_and_consume_are_tracked_in_conservation(ledger):
    ledger.produce("a", Asset.FOOD, 5, tick=1, reason="harvest")
    ledger.consume("a", Asset.FOOD, 3, tick=1, reason="eat")
    assert ledger.total(Asset.FOOD) == 12
    assert ledger.flows()["produced"][Asset.FOOD] == 5
    assert ledger.flows()["consumed"][Asset.FOOD] == 3
    ledger.check_conservation()


def test_conservation_check_detects_tampering(ledger):
    ledger._balances["a"][Asset.FOOD] += 1  # simulate a bug that bypasses the API
    with pytest.raises(ConservationError):
        ledger.check_conservation()


def test_unknown_account_and_self_transfer_rejected(ledger):
    with pytest.raises(InvalidOperation):
        ledger.transfer("a", "nobody", Asset.COIN, 1, tick=1, reason="test")
    with pytest.raises(InvalidOperation):
        ledger.transfer("a", "a", Asset.COIN, 1, tick=1, reason="test")


def test_operations_are_journalled(ledger):
    ledger.transfer("a", "b", Asset.FOOD, 2, tick=7, reason="sale")
    last = ledger.journal[-1]
    assert (last.tick, last.src, last.dst, last.asset, last.qty, last.reason) == (
        7,
        "a",
        "b",
        Asset.FOOD,
        2,
        "sale",
    )
