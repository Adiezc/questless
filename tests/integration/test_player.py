# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M7: the player loop (T2), save/load and exact replay (T8)."""

import json

import pytest

from questless.api import Simulation
from questless.contracts.model import ContractKind, Status
from questless.persistence import ReplayMismatch, load, save
from questless.player import ActionError, Quote, quote_buy, quote_caravan
from questless.sim.entities import ESCROW, OUTSIDE, PLAYER
from questless.sim.ledger import Asset
from tests.conftest import SCENARIOS


@pytest.fixture
def sim():
    return Simulation.from_scenario(SCENARIOS / "iron_shortage.toml")


def _first_iron_contract(sim):
    while True:
        assert sim.day < 60, "no iron contract by day 60"
        for cid in sim.step():
            c = sim.contract(cid)
            if c.good is Asset.IRON_ORE and c.kind is ContractKind.GUILD_SUPPLY:
                return c


def test_t2_completing_a_contract_moves_goods_and_pays_the_player(sim):
    c = _first_iron_contract(sim)
    sim.accept(c.id)
    coin_before = sim.player()["coin"]
    arrival = sim.caravan("iron_ore", c.qty)
    caravan_cost = coin_before - sim.player()["coin"]
    sim.step(arrival - sim.day)
    assert sim.player()["goods"]["iron_ore"] == c.qty

    ledger = sim.world.ledger
    held = {n: ledger.balance(n, Asset.IRON_ORE) for n in c.beneficiaries}
    escrow = ledger.balance(ESCROW, Asset.COIN)
    sim.deliver(c.id)

    assert c.status is Status.FULFILLED
    for npc_id, qty in c.beneficiaries.items():
        assert ledger.balance(npc_id, Asset.IRON_ORE) == held[npc_id] + qty
    assert ledger.balance(ESCROW, Asset.COIN) == escrow - c.reward
    assert sim.player()["coin"] == coin_before - caravan_cost + c.reward
    assert sim.player()["reputation"]["blacksmiths"] == c.rep_reward

    sim.step(7)
    assert c.outcome["before"] and c.outcome["after"]  # recorded for the dashboard


def test_t2_delivery_restores_production_versus_the_counterfactual():
    """Same seed, same actions, one difference: whether the ore is delivered. Over the next week
    the smiths who received it craft clearly more than in the run where it was withheld."""

    def crafted_after(deliver: bool) -> int:
        sim = Simulation.from_scenario(SCENARIOS / "iron_shortage.toml")
        c = _first_iron_contract(sim)
        sim.accept(c.id)
        sim.step(sim.caravan("iron_ore", c.qty) - sim.day)
        if deliver:
            sim.deliver(c.id)
        sim.step(7)
        history = (list(sim.world.npcs[n].history)[-7:] for n in c.beneficiaries)
        return sum(sum(r.produced.values()) for h in history for r in h)

    with_delivery, without = crafted_after(True), crafted_after(False)
    assert with_delivery > 1.3 * without


def test_buying_takes_real_supply_and_conserves_everything(sim):
    sim.step(5)
    ledger = sim.world.ledger
    totals = ledger.totals()
    bought = sim.buy("food", 10)
    assert 0 < bought <= 10
    assert ledger.balance(PLAYER, Asset.FOOD) == bought
    assert ledger.totals() == totals
    sim.world.check_invariants()


def test_caravan_draws_on_finite_outside_stock(sim):
    outside = sim.world.ledger.balance(OUTSIDE, Asset.IRON_ORE)
    sim.caravan("iron_ore", 5)
    assert sim.world.ledger.balance(OUTSIDE, Asset.IRON_ORE) == outside - 5
    with pytest.raises(ActionError):
        sim.caravan("tools", 10**6)  # more than the next town has


@pytest.mark.parametrize(
    "action, args",
    [
        ("deliver", {"contract_id": "C-9999"}),
        ("buy", {"good": "coin", "qty": 1}),
        ("buy", {"good": "food", "qty": 0}),
        ("caravan", {"good": "food", "qty": 10**9}),
        ("shock", {"effect": "site_output", "factor": 0.5, "duration": 5, "name": "x"}),
    ],
)
def test_invalid_actions_change_nothing(sim, action, args):
    sim.step(3)
    before = sim.world.state_hash()
    with pytest.raises(ActionError):
        getattr(sim, action)(**args)
    assert sim.world.state_hash() == before


def test_cannot_deliver_without_the_goods(sim):
    c = _first_iron_contract(sim)
    sim.accept(c.id)
    with pytest.raises(ActionError):
        sim.deliver(c.id)


def test_abandoning_reopens_the_contract_and_costs_reputation(sim):
    c = _first_iron_contract(sim)
    sim.accept(c.id)
    sim.abandon(c.id)
    assert c.status is Status.OPEN
    assert sim.player()["reputation"]["blacksmiths"] == -c.rep_reward


def test_t8_save_load_replays_exactly(sim, tmp_path):
    c = _first_iron_contract(sim)
    sim.accept(c.id)
    sim.caravan("iron_ore", c.qty)
    sim.shock("transport_capacity", 0.5, 10, "Bandits")
    sim.step(4)
    sim.deliver(c.id)
    sim.step(6)
    path = save(sim.world, tmp_path / "run.json")

    restored = load(path)
    assert restored.state_hash() == sim.world.state_hash()
    # ...and both continue identically.
    restored.step(20)
    sim.step(20)
    assert restored.state_hash() == sim.world.state_hash()


def test_tampered_save_is_rejected(sim, tmp_path):
    sim.step(30)
    path = save(sim.world, tmp_path / "run.json")
    data = json.loads(path.read_text())
    data["scenario"]["scenario"]["seed"] += 1
    path.write_text(json.dumps(data))
    with pytest.raises(ReplayMismatch):
        load(path)


def test_m16_2_quote_is_pure_and_matches_what_sourcing_costs(sim):
    """The card's estimate changes nothing, and following it costs exactly what it said."""
    c = _first_iron_contract(sim)
    before = sim.world.state_hash()
    quote = sim.quote(c.id)
    assert sim.world.state_hash() == before
    assert quote is not None and quote.profit == c.reward - quote.cost

    sim.accept(c.id)
    coin = sim.player()["coin"]
    if quote.source == "market":
        assert sim.buy("iron_ore", c.qty) == c.qty
    else:
        assert quote.source == "caravan"
        sim.step(sim.caravan("iron_ore", c.qty) - sim.day)
    assert coin - sim.player()["coin"] == quote.cost
    sim.deliver(c.id)
    assert sim.player()["coin"] == coin + quote.profit


def test_m16_2_quote_counts_goods_in_hand_and_skips_late_caravans(sim):
    c = _first_iron_contract(sim)
    sim.accept(c.id)
    sim.step(sim.caravan("iron_ore", c.qty) - sim.day)
    assert sim.quote(c.id) == Quote("in hand", 0, c.reward)

    late = Simulation.from_scenario(SCENARIOS / "iron_shortage.toml")
    c = _first_iron_contract(late)
    late.step(c.deadline_tick - late.config.contracts.caravan_days - late.day)
    # A caravan is on offer, but ordered today it would land on the deadline; nobody sells ore.
    assert quote_caravan(late.world, c.good, c.qty) is not None
    assert quote_buy(late.world, c.good, c.qty) is None
    assert late.quote(c.id) is None


def test_m16_2_transport_quote_is_the_whole_reward():
    sim = Simulation.from_scenario(SCENARIOS / "bandits.toml")
    for _ in range(90):
        for cid in sim.step():
            c = sim.contract(cid)
            if c.kind is ContractKind.TRANSPORT:
                assert sim.quote(cid) == Quote("haul", 0, c.reward)
                return
    pytest.skip("no transport contract in 90 days of bandits")
