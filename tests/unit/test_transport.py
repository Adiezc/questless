# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
import dataclasses

from questless.config import ShockConfig, ShockEffect
from questless.sim.entities import OUTSIDE, Profession
from questless.sim.ledger import Asset
from questless.sim.transport import ship
from questless.sim.world import build_world


def _load_sites(world, qty):
    for npc in world.npcs_by_profession(Profession.MINER):
        world.ledger.transfer(
            OUTSIDE, npc.site_account, Asset.IRON_ORE, qty, tick=world.tick, reason="test"
        )


def test_shipping_is_capped_by_capacity_and_keeps_ownership(baseline):
    world = build_world(baseline)
    _load_sites(world, 100)
    miner = world.npcs_by_profession(Profession.MINER)[0]
    before = world.ledger.balance(miner.account, Asset.IRON_ORE)
    report = ship(world)
    assert report.shipped == report.capacity < report.backlog
    moved = world.ledger.balance(miner.account, Asset.IRON_ORE) - before
    assert moved > 0
    assert world.ledger.balance(miner.site_account, Asset.IRON_ORE) == 100 - moved


def test_everything_ships_when_capacity_suffices(baseline):
    world = build_world(baseline)
    _load_sites(world, 1)
    report = ship(world)
    assert report.shipped == report.backlog == 16


def test_transport_shock_cuts_capacity(baseline):
    shock = ShockConfig("Bandits", ShockEffect.TRANSPORT_CAPACITY, 0, 10, 0.5)
    normal = ship(build_world(baseline))
    shocked = ship(build_world(dataclasses.replace(baseline, shocks=(shock,))))
    assert (
        shocked.capacity == normal.capacity // 2 or abs(shocked.capacity - normal.capacity / 2) <= 1
    )


def test_haulage_fees_move_coin_from_producers_to_merchants(baseline):
    world = build_world(baseline)
    _load_sites(world, 5)
    merchants = world.npcs_by_profession(Profession.MERCHANT)
    merchant_coin = sum(world.ledger.balance(m.account, Asset.COIN) for m in merchants)
    totals = world.ledger.totals()
    report = ship(world)
    assert report.fees_paid > 0
    gained = sum(world.ledger.balance(m.account, Asset.COIN) for m in merchants) - merchant_coin
    assert gained == report.fees_paid
    assert world.ledger.totals() == totals
