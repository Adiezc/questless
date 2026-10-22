from questless.finance.credit import score
from questless.finance.obligations import ObligationRegistry


def test_credit_score_baseline():
    reg = ObligationRegistry()
    # No history defaults to neutral score
    assert score("npc:1", reg) == 650


def test_credit_score_improves_with_repayment():
    reg = ObligationRegistry()
    ob1 = reg.open("npc:1", "town", 100, 0.05, [15], "escrow:1", tick=0)
    reg.settle(ob1.id)

    ob2 = reg.open("npc:1", "town", 100, 0.05, [30], "escrow:1", tick=15)
    reg.settle(ob2.id)

    # Clean repayment history with 0 debt yields high score
    assert score("npc:1", reg, annual_income=200, current_tick=35) >= 750


def test_credit_score_drops_on_default():
    reg = ObligationRegistry()
    ob = reg.open("npc:2", "town", 150, 0.10, [15], "escrow:2", tick=0)
    reg.default(ob.id)

    # Defaults and unpaid debt drop score substantially
    sc = score("npc:2", reg, annual_income=100, current_tick=20)
    assert sc < 600
