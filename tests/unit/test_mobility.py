# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Job switching (src/questless/sim/mobility.py): off by default; only NPCs that can't work move;
a move keeps every coin and good, the guild books and the contract board consistent; replays."""

import dataclasses
from pathlib import Path

import pytest

from questless.audit import audit
from questless.config import ConfigError, load_scenario, parse_scenario, to_dict
from questless.persistence import replay
from questless.policy import load
from questless.sim.entities import Profession
from questless.sim.mobility import UNTIL
from questless.sim.world import build_world
from tests.conftest import SCENARIOS

POLICIES = Path(__file__).resolve().parents[2] / "experiments" / "stress" / "policies"


@pytest.fixture(scope="module")
def switching():
    _, cfg = load(POLICIES / "job_switching.toml")
    world = build_world(dataclasses.replace(cfg, seed=1))
    world.step(500)  # step() checks conservation and the board every day
    moves = [m for s in world.stats for m in s.moves]
    assert moves, "this seed needs at least one move for the tests below"
    return world, moves


def test_off_by_default(baseline):
    assert not baseline.mobility.enabled
    world = build_world(baseline)
    world.step(200)
    assert not any(s.moves for s in world.stats)
    assert "profession" not in world.state_dict()["npcs"]["npc_000"]  # hashes unchanged


def test_only_npcs_that_could_not_work_move(switching):
    world, moves = switching
    cfg = world.config.mobility
    for m in moves:  # each move clears both bars against what the NPC actually earned
        assert m.old is not m.new
        assert m.expected >= cfg.margin * m.realised, m
        assert m.expected - m.realised >= cfg.min_gain, m
    per_day = {}
    for s in world.stats:
        per_day[s.tick] = len(s.moves)
    assert max(per_day.values()) <= cfg.max_per_day


def test_a_moved_npc_belongs_where_it_now_works(switching):
    world, moves = switching
    for npc in world.npcs.values():
        gid = next(
            (g for g, gc in world.config.guilds.items() if npc.profession in gc.professions),
            None,
        )
        assert npc.guild_id == gid, npc.id
        assert npc.site is world.config.professions[npc.profession].site
        assert world.ledger.has_account(npc.site_account)
    for guild in world.guilds.values():
        assert guild.members == sorted(guild.members)
        assert all(world.npcs[m].guild_id == guild.id for m in guild.members)
    for m in moves:
        npc = world.npcs[m.npc_id]
        assert npc.carry[UNTIL] > 0  # cooldown set


def test_a_switching_world_replays_and_its_contracts_rebuild(switching):
    world, _ = switching
    assert world.state_dict()["npcs"]["npc_000"]["profession"]  # professions are hashed
    assert replay(world.config, world.actions, world.tick).state_hash() == world.state_hash()
    assert all(not problems for problems in audit(world).values())


def test_mobility_settings_round_trip_and_validate(baseline):
    cfg = dataclasses.replace(
        baseline, mobility=dataclasses.replace(baseline.mobility, enabled=True, window=25)
    )
    assert parse_scenario(to_dict(cfg)) == cfg
    raw = to_dict(cfg)
    raw["mobility"]["professions"] = ["guard", "miner"]
    with pytest.raises(ConfigError, match="not guard or merchant"):
        parse_scenario(raw)
    raw = to_dict(cfg)
    raw["claims"]["enabled"] = True
    with pytest.raises(ConfigError, match="mobility and claims"):
        parse_scenario(raw)


@pytest.mark.slow
def test_switching_and_loans_end_hunger_and_keep_prices_near_base():
    """The combined policy over five seeds and two years: tools within 40% of base in the
    second year, and almost nobody permanently hungry (3 to 4 NPCs without either policy)."""
    from questless.sim.ledger import Asset

    _, cfg = load(POLICIES / "job_switching_and_loans.toml")
    base = cfg.goods[Asset.TOOLS].base_price
    for seed in range(1, 6):
        world = build_world(dataclasses.replace(cfg, seed=seed))
        world.step(730)
        second_year = world.stats[365:]
        tools = sum(s.prices[Asset.TOOLS] for s in second_year) / len(second_year)
        hungry = sum(s.hungry_npcs for s in second_year) / len(second_year)
        assert 0.6 * base < tools < 1.4 * base, (seed, tools)
        assert hungry < 1.0, (seed, hungry)
        assert world.npcs_by_profession(Profession.BLACKSMITH)  # smithing never empties


def test_the_scenario_files_leave_mobility_off():
    for path in sorted(SCENARIOS.glob("*.toml")):
        assert not load_scenario(path).mobility.enabled, path.name
