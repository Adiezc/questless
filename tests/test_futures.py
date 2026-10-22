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
