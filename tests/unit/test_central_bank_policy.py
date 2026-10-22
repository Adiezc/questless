"""Tests for M20 Central Bank, CPI, and Monetary Policy."""

from questless.api import Simulation
from questless.finance.central_bank import CentralBank
from questless.sim.entities import CENTRAL_BANK, Asset


def test_central_bank_policy_lifecycle():
    sim = Simulation.from_scenario("scenarios/baseline.toml", seed=42)
    world = sim.world

    # Ensure CENTRAL_BANK account exists and is sealed
    if not world.ledger.has_account(CENTRAL_BANK):
        world.ledger.add_empty_account(CENTRAL_BANK)

    cb = CentralBank()
    world.central_bank = cb

    # Initial conservation check
    world.ledger.check_conservation()

    # Step simulation for 15 days with central bank active
    for _ in range(15):
        world.step(1)
        world.ledger.check_conservation()

    # Check CPI and policy rate values recorded in stats
    latest_stats = world.stats[-1]
    assert latest_stats.cpi > 0
    assert 0.01 <= latest_stats.policy_rate <= 0.25

    # Test Discount window emergency borrowing
    merchants_acct = "guild:merchants"
    if not world.ledger.has_account(merchants_acct):
        world.ledger.add_empty_account(merchants_acct)

    init_merch_coin = world.ledger.balance(merchants_acct, Asset.COIN)
    cb.borrow_discount_window(world, "merchants", 200)

    assert world.ledger.balance(merchants_acct, Asset.COIN) == init_merch_coin + 200
    world.ledger.check_conservation()

    # Test Lobby nudge
    if "merchants" in world.guilds:
        merchants = world.guilds["merchants"]
        merchants.reputation["player"] = 50
        prev_target = cb.target_inflation
        assert cb.lobby_nudge(world, "merchants", "dovish") is True
        assert cb.target_inflation > prev_target
        assert merchants.reputation["player"] == 40
