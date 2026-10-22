from questless.finance.obligations import (
    ObligationRegistry,
    ObligationStatus,
)


def test_obligation_lifecycle():
    reg = ObligationRegistry()
    ob = reg.open(
        debtor="npc:101",
        creditor="guild:blacksmiths",
        principal=100,
        rate=0.10,
        schedule=[15, 30],
        collateral_account="escrow:101",
        tick=10,
    )
    assert ob.id == "OB-1"
    assert ob.status == ObligationStatus.ACTIVE
    assert ob.total_due() == 110
    assert ob.remaining_due() == 110

    # Due today queries
    assert len(reg.due_today(10)) == 0
    assert len(reg.due_today(15)) == 1
    assert reg.due_today(15)[0].id == "OB-1"

    # Partial settlement
    reg.settle("OB-1", amount=50)
    assert ob.paid == 50
    assert ob.remaining_due() == 60
    assert ob.status == ObligationStatus.ACTIVE

    # Full settlement
    reg.settle("OB-1", amount=60)
    assert ob.remaining_due() == 0
    assert ob.status == ObligationStatus.SETTLED


def test_obligation_serialization():
    reg = ObligationRegistry()
    ob = reg.open(
        debtor="npc:202",
        creditor="town:elders",
        principal=200,
        rate=0.05,
        schedule=[20],
        collateral_account="escrow:202",
        tick=5,
    )
    reg.default(ob.id)
    assert ob.status == ObligationStatus.DEFAULTED

    data = reg.to_dict()
    restored = ObligationRegistry.from_dict(data)
    assert restored.next_id == reg.next_id
    assert "OB-1" in restored.obligations
    r_ob = restored.obligations["OB-1"]
    assert r_ob.debtor == "npc:202"
    assert r_ob.status == ObligationStatus.DEFAULTED
