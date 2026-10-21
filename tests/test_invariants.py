# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Simulation invariants under adversarial play.

A seeded "chaos player" takes random actions (valid and invalid) and fires random shocks for 120
days. World invariants are checked on every tick by the engine itself (coin and goods conserved,
no negative balances, empty clearing account, escrow equal to live rewards, caps, no duplicate
needs); this test adds contract-level checks and replays the whole session from its log.
"""

import random

import pytest

from questless.api import Simulation
from questless.contracts.model import Status
from questless.contracts.provenance import verify
from questless.persistence import replay
from questless.player import ActionError
from questless.sim.ledger import GOODS
from tests.conftest import SCENARIOS


def _chaos_session(seed: int, days: int = 120) -> tuple[Simulation, dict[str, int]]:
    rng = random.Random(seed)
    sim = Simulation.from_scenario(SCENARIOS / "baseline.toml", seed=seed)
    tally = {"ok": 0, "rejected": 0}
    goods = [str(g) for g in GOODS]
    for _ in range(days):
        for _ in range(rng.randint(0, 3)):
            ids = [c.id for c in sim.contracts()] or ["C-0001"]
            choice = rng.choice(["accept", "deliver", "abandon", "buy", "caravan", "shock"])
            try:
                if choice in ("accept", "deliver", "abandon"):
                    getattr(sim, choice)(rng.choice(ids))
                elif choice in ("buy", "caravan"):
                    getattr(sim, choice)(rng.choice(goods), rng.randint(-2, 40))
                elif rng.random() < 0.15:  # shocks are rarer
                    site = rng.choice(["mine", "farms", None])
                    effect = "transport_capacity" if site is None else "site_output"
                    sim.shock(
                        effect, rng.choice([0.0, 0.3, 1.5]), rng.randint(3, 25), "chaos", site
                    )
                tally["ok"] += 1
            except ActionError:
                tally["rejected"] += 1
        sim.step()
    return sim, tally


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_invariants_survive_a_chaos_player(seed):
    sim, tally = _chaos_session(seed)  # raises on any invariant violation, on any tick
    assert tally["ok"] > 20 and tally["rejected"] > 20  # both paths were exercised
    cfg = sim.config.contracts
    for c in sim.contracts():
        assert c.reward >= cfg.min_reward
        assert c.deadline_tick > c.created_tick
        assert verify(sim.world, c) == [], c.id
        if c.status is Status.FULFILLED:
            assert c.accepted_by == "player"
    for s in sim.world.stats:
        assert len(s.contracts.created) <= cfg.max_new_per_tick
        assert s.contracts.live <= cfg.max_open


def test_chaos_session_replays_exactly():
    sim, _ = _chaos_session(seed=4, days=80)
    rebuilt = replay(sim.config, sim.world.actions, sim.day)
    assert rebuilt.state_hash() == sim.world.state_hash()
