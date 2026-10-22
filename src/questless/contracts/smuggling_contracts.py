"""Smuggling contracts and faction reputation mechanics (M19.4 & M19.5).

Defines:
- Enforcement contracts (town-funded) to intercept smuggling runs.
- Smuggling run contracts (smuggler-funded) to deliver contraband.
- Reputation mechanics across town, Merchants Guild, and Smuggler faction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from questless.contracts.model import Contract, ContractKind, Status
from questless.contracts.provenance import Evidence, Provenance
from questless.sim.entities import ESCROW, OUTSIDE, TOWN, Asset

if TYPE_CHECKING:
    from questless.sim.world import World

SMUGGLERS = "smugglers"


def post_enforcement_contract(world: World, good: Asset, bounty: int = 150) -> Contract | None:
    """Town-funded enforcement contract to intercept smuggling runs (M19.4).

    Bounty is escrowed from the Town treasury.
    """
    if world.ledger.balance(TOWN, Asset.COIN) < bounty:
        return None

    cid = f"C-{world.contracts.next_id:04d}"
    world.contracts.next_id += 1

    # Escrow bounty from Town
    world.ledger.transfer(
        TOWN,
        ESCROW,
        Asset.COIN,
        bounty,
        tick=world.tick,
        reason=f"escrow enforcement bounty {cid}",
    )

    prov = Provenance(
        chain=(
            Evidence(
                tick=world.tick,
                kind="town_emergency",
                subject=TOWN,
                metric="enforcement_intercept",
                value=float(bounty),
            ),
        ),
        world_hash=world.state_hash(),
    )

    contract = Contract(
        id=cid,
        kind=ContractKind.ENFORCEMENT,
        requester=TOWN,
        funder=TOWN,
        good=good,
        qty=1,
        reward=bounty,
        deadline_tick=world.tick + 10,
        reason=f"Town Watch bounty: intercept illicit {good.value} smuggling runs.",
        status=Status.OPEN,
        created_tick=world.tick,
        beneficiaries={TOWN: 1},
        rep_reward=15,
        dedup_key=(ContractKind.ENFORCEMENT.value, TOWN, str(good)),
        provenance=prov,
    )
    world.contracts.contracts[cid] = contract
    return contract


def post_smuggling_run_contract(
    world: World,
    good: Asset,
    qty: int = 5,
    reward: int = 200,
) -> Contract | None:
    """Smuggler-funded run contract to carry contraband past town guards (M19.4).

    Reward is escrowed from the Smugglers faction account.
    """
    if world.ledger.balance(SMUGGLERS, Asset.COIN) < reward:
        return None
    if world.ledger.balance(OUTSIDE, good) < qty:
        return None

    cid = f"C-{world.contracts.next_id:04d}"
    world.contracts.next_id += 1

    # Escrow reward from Smugglers
    world.ledger.transfer(
        SMUGGLERS,
        ESCROW,
        Asset.COIN,
        reward,
        tick=world.tick,
        reason=f"escrow smuggling run reward {cid}",
    )

    prov = Provenance(
        chain=(
            Evidence(
                tick=world.tick,
                kind="need_persisted",
                subject=SMUGGLERS,
                metric="contraband_demand",
                value=float(qty),
            ),
        ),
        world_hash=world.state_hash(),
    )

    contract = Contract(
        id=cid,
        kind=ContractKind.SMUGGLING_RUN,
        requester=SMUGGLERS,
        funder=SMUGGLERS,
        good=good,
        qty=qty,
        reward=reward,
        deadline_tick=world.tick + 7,
        reason=f"Smuggler syndicate run: deliver {qty} {good.value} past the guard checkpoints.",
        status=Status.OPEN,
        created_tick=world.tick,
        beneficiaries={SMUGGLERS: 1},
        rep_reward=20,
        dedup_key=(ContractKind.SMUGGLING_RUN.value, SMUGGLERS, str(good)),
        provenance=prov,
    )
    world.contracts.contracts[cid] = contract
    return contract


def update_faction_reputation(
    world: World,
    contract: Contract,
    accepted_by: str,
    outcome: str,
) -> dict[str, int]:
    """Reputation updates across factions and guilds (M19.5).

    - Completing Enforcement: Town +15, Merchants Guild +10, Smugglers -20.
    - Completing Smuggling Run: Smugglers +20, Town -15, Merchants Guild -10.
    - Failing / Intercepted: Reversed penalties.
    """
    if not hasattr(world, "faction_reputations"):
        world.faction_reputations = {
            TOWN: {accepted_by: 0},
            SMUGGLERS: {accepted_by: 0},
        }

    deltas: dict[str, int] = {}

    if contract.kind == ContractKind.ENFORCEMENT:
        if outcome == "completed":
            deltas[TOWN] = 15
            deltas[SMUGGLERS] = -20
            # Merchants guild likes enforcement
            merchants = world.guilds.get("merchants")
            if merchants:
                merchants.reputation[accepted_by] = max(
                    -100, min(100, merchants.reputation.get(accepted_by, 0) + 10)
                )
        else:
            deltas[TOWN] = -10
            deltas[SMUGGLERS] = 5

    elif contract.kind == ContractKind.SMUGGLING_RUN:
        if outcome == "completed":
            deltas[SMUGGLERS] = 20
            deltas[TOWN] = -15
            merchants = world.guilds.get("merchants")
            if merchants:
                merchants.reputation[accepted_by] = max(
                    -100, min(100, merchants.reputation.get(accepted_by, 0) - 10)
                )
        else:
            deltas[SMUGGLERS] = -15
            deltas[TOWN] = 5

    # Apply deltas clamped between -100 and +100
    for faction, delta in deltas.items():
        current = world.faction_reputations.setdefault(faction, {}).get(accepted_by, 0)
        world.faction_reputations[faction][accepted_by] = max(-100, min(100, current + delta))

    return deltas
