# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Aggregate transport: merchants haul goods from mine and farm stockpiles to the market.

No routes or carts: total daily capacity is the sum of merchant capacities (scaled by their
productivity and any transport shock), shared pro rata across everything waiting to be moved.
Ownership never changes in transit; goods move from ``npc_x@site`` to ``npc_x``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from questless.sim.alloc import allocate, split
from questless.sim.behaviour import productivity
from questless.sim.entities import MARKET, Profession
from questless.sim.ledger import GOODS, Asset

if TYPE_CHECKING:
    from questless.sim.world import World


@dataclass(frozen=True, slots=True)
class TransportReport:
    capacity: int
    backlog: int  # units waiting at sites before shipping
    shipped: int
    fees_paid: int
    fees_waived: int  # owed by producers who had no coin; goods still ship


def ship(world: World) -> TransportReport:
    cfg = world.config.transport
    merchants = world.npcs_by_profession(Profession.MERCHANT)
    # Capacity weights in thousandths keep fee shares integer.
    weights = {
        m.id: round(cfg.capacity_per_merchant * productivity(world, m) * 1000) for m in merchants
    }
    capacity = int(sum(weights.values()) / 1000 * world.modifiers.transport_capacity(world.tick))

    claims: list[tuple[str, int]] = []
    for npc in world.npcs_in_order():
        if npc.site_account == npc.account:
            continue
        for good in GOODS:
            qty = world.ledger.balance(npc.site_account, good)
            if qty:
                claims.append((f"{npc.id}|{good}", qty))
    rng = world.rng.stream("transport")
    shipments = allocate(capacity, claims, rng)

    shipped_value: dict[str, int] = {}
    for key, qty in shipments.items():
        if not qty:
            continue
        npc_id, good = key.split("|")
        npc = world.npcs[npc_id]
        world.ledger.transfer(
            npc.site_account, npc.account, Asset(good), qty, tick=world.tick, reason="haul"
        )
        shipped_value[npc_id] = shipped_value.get(npc_id, 0) + qty * world.unit_price(Asset(good))

    # Producers pay into a pool that is split across merchants once per day, so small fees are
    # not lost to rounding or always rounded up to the same merchant.
    paid = waived = 0
    for npc_id, value in sorted(shipped_value.items()):
        fee = int(value * cfg.fee_rate)
        fee_paid = min(fee, world.ledger.balance(npc_id, Asset.COIN))
        world.ledger.transfer(
            npc_id, MARKET, Asset.COIN, fee_paid, tick=world.tick, reason="haulage fee"
        )
        waived += fee - fee_paid
        paid += fee_paid
    for merchant_id, share in sorted(split(paid, weights.items(), rng).items()):
        world.ledger.transfer(
            MARKET, merchant_id, Asset.COIN, share, tick=world.tick, reason="haulage income"
        )

    return TransportReport(
        capacity=capacity,
        backlog=sum(q for _, q in claims),
        shipped=sum(shipments.values()),
        fees_paid=paid,
        fees_waived=waived,
    )
