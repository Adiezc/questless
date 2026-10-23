# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Contract validation: feasibility before posting, and board invariants checked every tick."""

from __future__ import annotations

from typing import TYPE_CHECKING

from questless.contracts.model import ContractKind
from questless.sim.entities import ESCROW, OUTSIDE
from questless.sim.ledger import Asset
from questless.sim.market import stock_target

if TYPE_CHECKING:
    from questless.contracts.engine import ContractBoard
    from questless.sim.world import World


class ContractInvariantError(AssertionError):
    pass


def obtainable(world: World, good: Asset, exclude: set[str] = frozenset()) -> int:
    """Units a player could get hold of today: NPC stock above target (buyable at market) plus
    what can be imported from outside. Goods nobody has and nobody can import are infeasible."""
    surplus = 0
    for npc in world.npcs_in_order():
        if npc.id in exclude:
            continue
        surplus += max(world.ledger.balance(npc.account, good) - stock_target(world, npc, good), 0)
    return surplus + world.ledger.balance(OUTSIDE, good)


def site_backlog(world: World, good: Asset) -> dict[str, int]:
    """Goods waiting at production sites, by owner."""
    return {
        n.id: q
        for n in world.npcs_in_order()
        if n.site_account != n.account and (q := world.ledger.balance(n.site_account, good))
    }


def check_board(world: World, board: ContractBoard) -> None:
    """Invariants: escrow holds exactly the rewards of live contracts; caps hold; at most one live
    contract per dedup key; every contract carries provenance and a positive, funded reward."""
    live = [c for c in board.contracts.values() if c.live]
    problems: list[str] = []
    escrow = world.ledger.balance(ESCROW, Asset.COIN)
    if escrow != sum(c.reward for c in live):
        problems.append(f"escrow {escrow} != live rewards {sum(c.reward for c in live)}")
    if len(live) > world.config.contracts.max_open:
        problems.append(f"{len(live)} live contracts exceed cap {world.config.contracts.max_open}")
    keys = [c.dedup_key for c in live]
    if len(keys) != len(set(keys)):
        problems.append("duplicate live contracts for the same need")
    # No NPC is a non-zero beneficiary of two live non-transport contracts for the same good (M13.7)
    beneficiary_pairs: list[tuple[str, Asset]] = [
        (npc_id, c.good)
        for c in live
        if c.kind is not ContractKind.TRANSPORT
        for npc_id, qty in c.beneficiaries.items()
        if qty > 0
    ]
    if len(beneficiary_pairs) != len(set(beneficiary_pairs)):
        problems.append("NPC is a beneficiary of multiple live contracts for the same good")
    for c in board.contracts.values():
        if not c.provenance.chain:
            problems.append(f"{c.id} has no provenance")
        if c.reward <= 0 or c.qty <= 0:
            problems.append(f"{c.id} has non-positive reward or quantity")
        if sum(c.beneficiaries.values()) != c.qty:
            problems.append(f"{c.id} beneficiaries do not add up to qty")
    if problems:
        raise ContractInvariantError("; ".join(problems))
