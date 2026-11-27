# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Working-capital loans for broke guild members (docs/VALIDATION.md D3): off unless a guild sets
``loan_limit``; lent and repaid through the ledger; sized so the borrower can actually bid."""

import dataclasses
from pathlib import Path

import pytest

from questless.config import ConfigError, parse_scenario, to_dict
from questless.policy import diff, load
from questless.sim.entities import Profession
from questless.sim.guilds import LOAN, loan_target
from questless.sim.ledger import Asset
from questless.sim.market import budget
from questless.sim.world import build_world

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "experiments" / "stress" / "policies" / "guild_loans.toml"


def _with_loans(cfg, limit=300):
    return dataclasses.replace(
        cfg,
        guilds={
            gid: dataclasses.replace(gc, policy=dataclasses.replace(gc.policy, loan_limit=limit))
            for gid, gc in cfg.guilds.items()
        },
    )


@pytest.fixture(scope="module")
def lending():
    from questless.config import load_scenario
    from tests.conftest import SCENARIOS

    world = build_world(_with_loans(load_scenario(SCENARIOS / "baseline.toml")))
    world.step(400)  # step() checks conservation every day
    return world


def test_loans_are_off_by_default(baseline):
    assert all(gc.policy.loan_limit == 0 for gc in baseline.guilds.values())
    world = build_world(baseline)
    world.step(200)
    assert all(r.loans == r.repaid == 0 for s in world.stats for r in s.guilds.values())
    assert not any(LOAN in n.carry for n in world.npcs.values())


def test_loans_go_out_and_come_back_within_their_limits(lending):
    reports = [r for s in lending.stats for r in s.guilds.values()]
    lent, repaid = sum(r.loans for r in reports), sum(r.repaid for r in reports)
    assert lent > 0 and repaid > 0
    outstanding = sum(n.carry.get(LOAN, 0) for n in lending.npcs.values())
    assert outstanding == lent - repaid  # every coin lent is repaid or still owed
    # The ledger's recent journal agrees with today's report.
    today = [e for e in lending.ledger.journal if e.tick == lending.tick - 1]
    assert sum(e.qty for e in today if e.reason == "guild loan") == sum(
        r.loans for r in lending.stats[-1].guilds.values()
    )
    for npc in lending.npcs.values():
        assert 0 <= npc.carry.get(LOAN, 0) <= 300
        if LOAN in npc.carry:  # guards have no guild; everyone else may borrow
            assert npc.profession is not Profession.GUARD
    guild = lending.guilds["blacksmiths"]
    floor = guild.policy.reserve // 2
    # Loans stop at the floor; a guild contract may escrow more later the same day.
    reports = [s.guilds["blacksmiths"] for s in lending.stats]
    assert all(r.treasury + r.escrowed >= floor for r in reports)


def test_a_loan_lets_a_broke_smith_bid_for_ore(lending):
    smith = lending.npcs_by_profession(Profession.BLACKSMITH)[0]
    wallet = lending.ledger.balance(smith.account, Asset.COIN)
    target = loan_target(lending, smith.id)
    if wallet < target:
        lending.ledger.transfer(
            lending.guilds["blacksmiths"].account,
            smith.account,
            Asset.COIN,
            target - wallet,
            tick=lending.tick,
            reason="test",
        )
    elif wallet > target:
        lending.ledger.transfer(
            smith.account, "town", Asset.COIN, wallet - target, tick=lending.tick, reason="test"
        )
    ore_for_one_craft = min(
        sum(lending.unit_price(a) * q for a, q in inputs.items())
        for inputs in lending.config.professions[Profession.BLACKSMITH].recipes.values()
    )
    assert budget(lending, smith, Asset.IRON_ORE) >= ore_for_one_craft


def test_the_policy_overlay_changes_only_the_loan_limit():
    base, policy = load(POLICY)
    changed = diff(base, policy)
    changed.pop("scenario.name")
    assert changed == {
        f"guilds.{gid}.policy.loan_limit": (0, 300)
        for gid in ("miners", "merchants", "blacksmiths")
    }


@pytest.mark.parametrize(
    "field, value, message",
    [("loan_limit", -1, "loan_limit"), ("loan_repay_share", 1.5, "loan_repay_share")],
)
def test_invalid_loan_settings_fail_loudly(baseline, field, value, message):
    raw = to_dict(baseline)
    raw["guilds"]["blacksmiths"]["policy"][field] = value
    with pytest.raises(ConfigError, match=message):
        parse_scenario(raw)


def test_loan_settings_survive_a_save_round_trip(baseline):
    cfg = _with_loans(baseline, 250)
    assert parse_scenario(to_dict(cfg)) == cfg
