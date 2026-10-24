# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M60: land and mine claims. Work rights that earn rent, traded by NPCs short of coin, with coin
conserved and every claim held by exactly one owner and worked by exactly one worker."""

import csv
import dataclasses
import statistics as st
import tomllib
from pathlib import Path

import pytest

from questless import export, policy
from questless.config import ConfigError, parse_scenario, to_dict
from questless.metrics import gini
from questless.sim import claims
from questless.sim.entities import TOWN
from questless.sim.ledger import Asset
from questless.sim.world import build_world
from tests.conftest import SCENARIOS

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "experiments" / "stress" / "policies" / "claims.toml"


@pytest.fixture
def raw_baseline() -> dict:
    with (SCENARIOS / "baseline.toml").open("rb") as fh:
        return tomllib.load(fh)


def _on(cfg, **kw):
    return dataclasses.replace(cfg, claims=dataclasses.replace(cfg.claims, enabled=True, **kw))


def test_off_by_default_changes_nothing(baseline):
    world = build_world(baseline)
    world.step(10)
    assert world.claims == {}
    assert all(s.claims is None and s.wealth_gini is None for s in world.stats)
    assert "claims" not in world.state_dict()


def test_every_gatherer_starts_owning_the_claim_they_work(baseline):
    world = build_world(_on(baseline))
    gatherers = [n for n in world.npcs_in_order() if world.config.professions[n.profession].output]
    assert len(world.claims) == len(gatherers) == 50
    assert all(c.owner == c.worker for c in world.claims.values())
    assert {c.site for c in world.claims.values()} == {"mine", "farms"}


def test_rent_is_a_share_of_output_and_never_goes_below_the_floor(baseline):
    world = build_world(_on(baseline, rent_share=0.5, rent_floor=40))
    claim = world.claims["mine-01"]
    landlord = next(n.id for n in world.npcs_in_order() if n.id != claim.worker)
    claim.owner = landlord
    tenant_start = world.ledger.balance(claim.worker, Asset.COIN)
    world.step(1)
    report = world.stats[-1].claims
    value = claim.output_value[-1]
    due = int(0.5 * value)
    assert report.paid_by[claim.worker] + report.rent_unpaid == due
    assert report.received_by[landlord] == report.paid_by[claim.worker]
    assert world.ledger.balance(claim.worker, Asset.COIN) >= min(40, tenant_start) or not due


def test_an_owner_short_of_coin_sells_to_the_richest_and_rents_it_back(baseline):
    world = build_world(_on(baseline, sell_below=30, buy_reserve=0))
    world.step(8)  # some output history, so claims have a price
    claim = world.claims["farms-01"]
    seller = claim.owner
    coin = world.ledger.balance(seller, Asset.COIN)
    world.ledger.transfer(seller, TOWN, Asset.COIN, coin - 5, tick=world.tick, reason="test")
    richest = max(
        (n for n in world.npcs_in_order() if n.id != seller),
        key=lambda n: (world.ledger.balance(n.account, Asset.COIN), -int(n.id[4:])),
    ).id
    cost = claims.price(world, claim)
    assert cost > 0
    before = world.ledger.balance(richest, Asset.COIN)
    report = claims.ClaimsReport()
    claims.trade(world, report)
    assert claim.owner == richest and claim.worker == seller
    assert world.ledger.balance(seller, Asset.COIN) == 5 + cost
    assert world.ledger.balance(richest, Asset.COIN) == before - cost
    assert report.sold >= 1
    world.check_invariants()


def test_a_year_of_trading_conserves_coin_and_claims(baseline):
    world = build_world(_on(baseline, sell_below=40))  # trades often
    world.step(365)  # check_invariants runs every tick, claims included
    assert len(world.claims) == 50
    workers = sorted(c.worker for c in world.claims.values())
    assert len(set(workers)) == 50
    # The journal keeps the most recent entries; compare only days it holds in full.
    first = min(e.tick for e in world.ledger.journal) + 1
    rent = sum(e.qty for e in world.ledger.journal if e.reason == "rent" and e.tick >= first)
    paid = sum(s.claims.rent_paid for s in world.stats if s.tick >= first)
    assert rent == paid
    assert sum(s.claims.sold for s in world.stats) > 0


def test_claims_concentrate_wealth_over_a_year(baseline):
    """With trading, the Gini of coin plus claims ends above a world where claims never trade."""
    diffs = []
    for seed in range(1, 6):
        cfg = dataclasses.replace(baseline, seed=seed)
        traded, frozen = build_world(_on(cfg)), build_world(_on(cfg, sell_below=0))
        traded.step(365)
        frozen.step(365)
        diffs.append(gini(claims.wealth(traded)) - gini(claims.wealth(frozen)))
    assert st.fmean(diffs) > 0.02, diffs


def test_same_seed_same_claims(baseline):
    a, b = build_world(_on(baseline, sell_below=40)), build_world(_on(baseline, sell_below=40))
    a.step(60)
    b.step(60)
    assert a.state_hash() == b.state_hash()
    assert claims.state(a) == claims.state(b)


@pytest.mark.parametrize(
    ("table", "message"),
    [
        ({"enabled": "yes"}, "true or false"),
        ({"rent_share": 1.5}, "between 0 and 1"),
        ({"price_days": 0}, "price_days"),
        ({"landlords": 3}, "landlords"),
    ],
)
def test_bad_claims_config_fails_loudly(raw_baseline, table, message):
    with pytest.raises(ConfigError, match=message):
        parse_scenario({**raw_baseline, "claims": table})


def test_claims_round_trip_and_are_a_rule_policies_may_change(raw_baseline):
    cfg = parse_scenario({**raw_baseline, "claims": {"enabled": True, "rent_share": 0.3}})
    assert parse_scenario(to_dict(cfg)) == cfg
    base, pol = policy.load(POLICY)
    assert pol.claims.enabled and not base.claims.enabled


def test_export_rent_columns_add_up(tmp_path):
    export.export(SCENARIOS / "baseline.toml", tmp_path, seeds=[1], policies=[POLICY], days=60)
    with (tmp_path / "npc_days.csv").open() as fh:
        npc = [r for r in csv.DictReader(fh) if r["arm"] == "claims"]
    with (tmp_path / "daily.csv").open() as fh:
        daily = {r["day"]: r for r in csv.DictReader(fh) if r["arm"] == "claims"}
    for day, row in daily.items():
        rows = [r for r in npc if r["day"] == day]
        assert sum(int(r["rent_paid"]) for r in rows) == int(row["rent_paid"])
        assert sum(int(r["rent_received"]) for r in rows) == int(row["rent_paid"])
        assert sum(int(r["claims_owned"]) for r in rows) == 50
        assert row["wealth_gini"] != ""
