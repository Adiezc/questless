from questless.finance.market_maker import ForwardQuote, MarketMaker
from questless.sim.ledger import Ledger


def test_forward_quote_calculation_and_evidence():
    mm = MarketMaker(base_carry=0.002, normal_cover_days=14.0)

    # Spot = 20 coin, Days = 10, normal cover (14 days) -> risk_factor = 1.0
    # carry_multiplier = 1 + 0.002 * 10 = 1.02
    # expected forward = 20 * 1.02 * 1.0 = 20.4 -> 20
    q = mm.quote(
        good="iron_ore",
        spot=20,
        days=10,
        stock_cover=14.0,
        treasury_balance=1000,
        tick=5,
    )

    assert q.forward == 20
    assert q.days == 10
    assert q.spot == 20
    assert q.risk_factor == 1.0
    assert q.max_qty == 500 // 20  # 50% of 1000 = 500 exposure // 20 = 25 contracts
    assert q.max_qty == 25

    # Evidence checking
    assert q.evidence["spot"] == 20
    assert q.evidence["days"] == 10
    assert q.evidence["stock_cover"] == 14.0
    assert q.evidence["carry_rate"] == 0.002
    assert q.evidence["treasury"] == 1000


def test_forward_quote_scarcity_risk_factor():
    mm = MarketMaker(base_carry=0.002, normal_cover_days=14.0)

    # Depleted stock: cover = 0 days -> risk factor 1.40
    # carry_multiplier = 1 + 0.002 * 30 = 1.06
    # spot = 100 -> forward = round(100 * 1.06 * 1.40) = 148
    q_depleted = mm.quote(
        good="iron_ore",
        spot=100,
        days=30,
        stock_cover=0.0,
        treasury_balance=1000,
        tick=1,
    )
    assert q_depleted.risk_factor == 1.40
    assert q_depleted.forward == 148

    # Abundant stock: cover = 20 days -> risk factor 1.0
    q_abundant = mm.quote(
        good="iron_ore",
        spot=100,
        days=30,
        stock_cover=20.0,
        treasury_balance=1000,
        tick=1,
    )
    assert q_abundant.risk_factor == 1.0
    assert q_abundant.forward == 106


def test_quote_board_with_ledger():
    ledger = Ledger()
    merchants_account = "guild:merchants"
    ledger.open_account(merchants_account)
    ledger.produce(merchants_account, "coin", 2000, tick=0, reason="init")

    mm = MarketMaker()
    spots = {"grain": 10, "iron_ore": 20, "tools": 50}
    covers = {"grain": 14.0, "iron_ore": 7.0, "tools": 21.0}

    board = mm.quote_board(
        goods_spot=spots,
        goods_cover=covers,
        ledger=ledger,
        guild_account=merchants_account,
        tick=10,
    )

    assert set(board.keys()) == {"grain", "iron_ore", "tools"}
    for g in board:
        assert set(board[g].keys()) == {10, 20, 30}
        q10 = board[g][10]
        q20 = board[g][20]
        q30 = board[g][30]
        # Longer horizons must have higher or equal forward price due to positive carry
        assert q30.forward >= q20.forward >= q10.forward


def test_forward_quote_serialization():
    q = ForwardQuote(
        good="grain",
        days=20,
        spot=15,
        forward=16,
        stock_cover=10.5,
        carry_rate=0.002,
        risk_factor=1.08,
        max_qty=30,
        tick=3,
        evidence={"spot": 15},
    )
    data = q.to_dict()
    restored = ForwardQuote.from_dict(data)
    assert restored == q
