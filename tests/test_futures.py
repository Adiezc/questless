from questless.finance.futures import Future, FuturesMarket, FutureStatus
from questless.finance.obligations import ObligationStatus
from questless.sim.ledger import Ledger


def test_future_opening_and_escrow_conservation():
    ledger = Ledger()
    buyer = "npc:buyer"
    seller = "npc:seller"

    ledger.open_account(buyer)
    ledger.open_account(seller)
    ledger.produce(buyer, "coin", 1000, tick=0, reason="init")
    ledger.produce(seller, "coin", 500, tick=0, reason="init")
    initial_total_coin = ledger.total("coin")
    assert initial_total_coin == 1500

    market = FuturesMarket()
    # Contract: 10 ore @ 20 coin = 200 notional. Seller collateral = 30% of 200 = 60 coin.
    f = market.open_future(
        ledger=ledger,
        good="iron_ore",
        qty=10,
        strike=20,
        delivery_tick=15,
        buyer=buyer,
        seller=seller,
        tick=5,
    )

    assert f.notional == 200
    assert f.collateral == 60
    assert f.status == FutureStatus.OPEN
    assert f.delivery_tick == 15

    # Check ledger balances after escrow
    assert ledger.balance(buyer, "coin") == 800
    assert ledger.balance(seller, "coin") == 440
    assert ledger.balance(f.buyer_escrow_account, "coin") == 200
    assert ledger.balance(f.seller_collateral_account, "coin") == 60

    # Invariant: escrow == open notional + collateral
    assert market.open_notional() == 200
    assert market.total_collateral() == 60
    assert market.total_escrow() == 260
    assert (
        ledger.balance(f.buyer_escrow_account, "coin")
        + ledger.balance(f.seller_collateral_account, "coin")
        == market.total_escrow()
    )

    # Invariant: total coins in ledger strictly conserved
    assert ledger.total("coin") == initial_total_coin

    # Check seller delivery obligation registered in M17 registry
    ob = market.registry.obligations[f.delivery_obligation_id]
    assert ob.debtor == seller
    assert ob.creditor == buyer
    assert ob.principal == 200
    assert ob.schedule == [15]
    assert ob.status == ObligationStatus.ACTIVE


def test_future_serialization():
    market = FuturesMarket()
    f = Future(
        id="FUT-1",
        good="grain",
        qty=5,
        strike=10,
        delivery_tick=20,
        buyer="buyer_1",
        seller="seller_1",
        buyer_escrow_account="escrow:buyer",
        seller_collateral_account="escrow:seller",
        delivery_obligation_id="OB-1",
        status=FutureStatus.OPEN,
        created_tick=1,
    )
    market.positions["FUT-1"] = f

    data = market.to_dict()
    restored = FuturesMarket.from_dict(data)

    assert "FUT-1" in restored.positions
    rf = restored.positions["FUT-1"]
    assert rf.id == "FUT-1"
    assert rf.notional == 50
    assert rf.collateral == 15
    assert rf.status == FutureStatus.OPEN


def test_future_physical_settlement_success():
    ledger = Ledger()
    buyer = "npc:buyer"
    seller = "npc:seller"

    ledger.open_account(buyer)
    ledger.open_account(seller)
    ledger.produce(buyer, "coin", 500, tick=0, reason="init")
    ledger.produce(seller, "coin", 200, tick=0, reason="init")
    # Seller has 10 units of iron_ore to deliver
    ledger.produce(seller, "iron_ore", 10, tick=0, reason="init")

    init_total_coin = ledger.total("coin")
    init_total_ore = ledger.total("iron_ore")

    market = FuturesMarket()
    f = market.open_future(
        ledger=ledger,
        good="iron_ore",
        qty=10,
        strike=25,
        delivery_tick=10,
        buyer=buyer,
        seller=seller,
        tick=1,
    )
    # Notional: 250, Collateral: 75
    assert ledger.balance(buyer, "coin") == 250
    assert ledger.balance(seller, "coin") == 125

    # Settle at tick 10 with spot price 30
    results = market.settle_tick(tick=10, ledger=ledger, spot_prices={"iron_ore": 30})
    assert len(results) == 1
    assert results[0]["status"] == "settled"
    assert f.status == FutureStatus.SETTLED

    # Buyer has received 10 iron_ore
    assert ledger.balance(buyer, "iron_ore") == 10
    assert ledger.balance(seller, "iron_ore") == 0

    # Seller received buyer escrow (250) + collateral return (75) = 125 + 325 = 450
    assert ledger.balance(seller, "coin") == 450
    assert ledger.balance(buyer, "coin") == 250

    # Escrow balances are now empty
    assert ledger.balance(f.buyer_escrow_account, "coin") == 0
    assert ledger.balance(f.seller_collateral_account, "coin") == 0

    # Invariants
    assert ledger.total("coin") == init_total_coin
    assert ledger.total("iron_ore") == init_total_ore
    assert market.total_escrow() == 0

    # Obligation settled
    ob = market.registry.obligations[f.delivery_obligation_id]
    assert ob.status == ObligationStatus.SETTLED


def test_future_default_and_compensation():
    ledger = Ledger()
    buyer = "npc:buyer"
    seller = "npc:seller"

    ledger.open_account(buyer)
    ledger.open_account(seller)
    ledger.produce(buyer, "coin", 500, tick=0, reason="init")
    ledger.produce(seller, "coin", 200, tick=0, reason="init")
    # Seller has 0 iron_ore (cannot deliver)

    init_total_coin = ledger.total("coin")

    market = FuturesMarket()
    f = market.open_future(
        ledger=ledger,
        good="iron_ore",
        qty=10,
        strike=25,
        delivery_tick=10,
        buyer=buyer,
        seller=seller,
        tick=1,
    )
    # Notional = 250. Collateral = 75.

    # Settle at tick 10 when spot has spiked to 30.
    # Compensation = (30 - 25) * 10 = 50 coin from collateral.
    results = market.settle_tick(tick=10, ledger=ledger, spot_prices={"iron_ore": 30})
    assert len(results) == 1
    assert results[0]["status"] == "defaulted"
    assert results[0]["compensation_paid"] == 50
    assert f.status == FutureStatus.DEFAULTED

    # Buyer gets refund of escrow (250) + compensation (50) = 550
    assert ledger.balance(buyer, "coin") == 550

    # Seller gets remaining collateral (75 - 50 = 25) + kept their unescrowed (125) = 150
    assert ledger.balance(seller, "coin") == 150

    # Total coin strictly conserved
    assert ledger.total("coin") == init_total_coin
    assert market.total_escrow() == 0

    # Obligation defaulted
    ob = market.registry.obligations[f.delivery_obligation_id]
    assert ob.status == ObligationStatus.DEFAULTED
