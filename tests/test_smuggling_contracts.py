from questless.api import Simulation
from questless.contracts.model import ContractKind, Status
from questless.contracts.smuggling_contracts import (
    SMUGGLERS,
    post_enforcement_contract,
    post_smuggling_run_contract,
    update_faction_reputation,
)
from questless.sim.entities import ESCROW, OUTSIDE, PLAYER, TOWN, Asset


def test_enforcement_and_run_contracts_lifecycle():
    sim = Simulation.from_scenario("scenarios/baseline.toml", seed=42)
    world = sim.world

    # Setup accounts
    if SMUGGLERS not in world.ledger.accounts():
        world.ledger.add_empty_account(SMUGGLERS)
    # Transfer coin from player to seed smugglers account (preserving coin conservation)
    world.ledger.transfer(PLAYER, SMUGGLERS, Asset.COIN, 500, tick=0, reason="seed_smugglers")
    world.ledger.produce(OUTSIDE, Asset.IRON_ORE, 50, tick=0, reason="init")

    init_town_coin = world.ledger.balance(TOWN, Asset.COIN)
    init_smuggler_coin = world.ledger.balance(SMUGGLERS, Asset.COIN)
    init_escrow = world.ledger.balance(ESCROW, Asset.COIN)

    # 1. Post Enforcement Contract
    c_enf = post_enforcement_contract(world, Asset.IRON_ORE, bounty=150)
    assert c_enf is not None
    assert c_enf.kind == ContractKind.ENFORCEMENT
    assert c_enf.funder == TOWN
    assert c_enf.reward == 150
    assert c_enf.status == Status.OPEN
    # Escrow deduction
    assert world.ledger.balance(TOWN, Asset.COIN) == init_town_coin - 150
    assert world.ledger.balance(ESCROW, Asset.COIN) == init_escrow + 150

    # 2. Post Smuggling Run Contract
    c_run = post_smuggling_run_contract(world, Asset.IRON_ORE, qty=5, reward=200)
    assert c_run is not None
    assert c_run.kind == ContractKind.SMUGGLING_RUN
    assert c_run.funder == SMUGGLERS
    assert c_run.reward == 200
    assert c_run.status == Status.OPEN
    # Escrow deduction
    assert world.ledger.balance(SMUGGLERS, Asset.COIN) == init_smuggler_coin - 200
    assert world.ledger.balance(ESCROW, Asset.COIN) == init_escrow + 350

    # Invariants: conservation holds
    world.ledger.check_conservation()

    # 3. Test Faction Reputation updates
    deltas_enf = update_faction_reputation(world, c_enf, PLAYER, "completed")
    assert deltas_enf[TOWN] == 15
    assert deltas_enf[SMUGGLERS] == -20
    assert world.faction_reputations[TOWN][PLAYER] == 15
    assert world.faction_reputations[SMUGGLERS][PLAYER] == -20

    deltas_run = update_faction_reputation(world, c_run, PLAYER, "completed")
    assert deltas_run[SMUGGLERS] == 20
    assert deltas_run[TOWN] == -15
    # Town reputation net: 15 - 15 = 0; Smugglers net: -20 + 20 = 0
    assert world.faction_reputations[TOWN][PLAYER] == 0
    assert world.faction_reputations[SMUGGLERS][PLAYER] == 0
