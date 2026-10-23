"""Tests for M13.5: Pay transport contracts only for the units actually hauled (Fixes #43)."""

from pathlib import Path

import pytest

from questless.api import Simulation
from questless.contracts.model import ContractKind
from questless.contracts.validation import check_board
from questless.player import ActionError
from questless.sim.entities import ESCROW, PLAYER, Asset

SCENARIOS = (
    Path(__file__).resolve().parent.parent / "scenarios"
    if (Path(__file__).resolve().parent.parent / "scenarios").exists()
    else Path("scenarios")
)


def test_transport_contract_pro_rata_payment_and_zero_haul_error():
    """Verify that:
    1. Transport contracts pay pro-rata for units actually hauled.
    2. The unhauled remainder is refunded to the funder.
    3. Delivering with zero backlog raises ActionError/ValueError and moves no coin.
    4. check_board and ledger conservation pass.
    """
    sim = Simulation.from_scenario(SCENARIOS / "bandits.toml", seed=42)
    world = sim.world

    # Find a transport contract
    transport_cid = None
    for _ in range(60):
        for cid in sim.step():
            c = sim.contract(cid)
            if c.kind is ContractKind.TRANSPORT:
                transport_cid = cid
                break
        if transport_cid:
            break

    assert transport_cid is not None, "A transport contract should appear in bandits.toml"

    c = world.contracts.contracts[transport_cid]
    # Accept the contract
    sim.accept(transport_cid)
    assert c.accepted_by == PLAYER

    # Artificially clear site stockpiles to simulate merchants having caught up
    # First, test zero haul rejection
    saved_site_stock = {}
    for nid in c.beneficiaries:
        npc = world.npcs[nid]
        bal = world.ledger.balance(npc.site_account, c.good)
        saved_site_stock[npc.site_account] = bal
        if bal > 0:
            world.ledger.transfer(
                npc.site_account,
                npc.account,
                c.good,
                bal,
                tick=world.tick,
                reason="simulate_empty_backlog",
            )

    # Delivering when backlog is 0 must raise ActionError
    escrow_before = world.ledger.balance(ESCROW, Asset.COIN)
    player_coin_before = world.ledger.balance(PLAYER, Asset.COIN)

    with pytest.raises(ActionError, match="has nothing left to haul"):
        sim.deliver(transport_cid)

    # Invariants unchanged after rejected zero haul
    assert world.ledger.balance(ESCROW, Asset.COIN) == escrow_before
    assert world.ledger.balance(PLAYER, Asset.COIN) == player_coin_before
    world.ledger.check_conservation()

    # Now restore a partial haul (e.g. 50% of the requested backlog)
    total_wanted = c.qty
    partial_haul = total_wanted // 2
    remaining_to_seed = partial_haul

    for site_acct, original_bal in saved_site_stock.items():
        if remaining_to_seed <= 0:
            break
        to_return = min(remaining_to_seed, original_bal)
        # Transfer back to site_account from npc.account
        # Extract npc_id from site_account (e.g. "npc_000@mine" -> "npc_000")
        nid = site_acct.split("@")[0]
        world.ledger.transfer(
            nid, site_acct, c.good, to_return, tick=world.tick, reason="restore_partial_backlog"
        )
        remaining_to_seed -= to_return

    actual_backlog_available = sum(
        min(qty, world.ledger.balance(world.npcs[nid].site_account, c.good))
        for nid, qty in c.beneficiaries.items()
    )
    assert actual_backlog_available > 0
    assert actual_backlog_available < total_wanted

    # Check quote reflects actual backlog
    quote = sim.quote(transport_cid)
    assert quote is not None
    expected_est_reward = (c.reward * actual_backlog_available) // c.qty
    assert quote.profit == expected_est_reward

    funder_coin_before = world.ledger.balance(c.funder, Asset.COIN)

    # Deliver contract with partial backlog
    sim.deliver(transport_cid)

    # Check pro-rata payout
    expected_player_pay = (c.reward * actual_backlog_available) // c.qty
    expected_refund = c.reward - expected_player_pay

    assert world.ledger.balance(PLAYER, Asset.COIN) == player_coin_before + expected_player_pay
    assert world.ledger.balance(c.funder, Asset.COIN) == funder_coin_before + expected_refund
    assert c.outcome.get("hauled") == actual_backlog_available

    # Invariants hold
    world.ledger.check_conservation()
    check_board(world, world.contracts)
