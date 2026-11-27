# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Golden state hashes: each shipped scenario, at its own seed, run for 60 days, must reach
exactly this state. The determinism tests compare two runs in one interpreter; these pin the
result across Python versions, platforms and commits, so an accidental behaviour change fails
here even when every other test still passes.

A deliberate change to the simulation changes these hashes. Check `questless diff` first, then
update the table with:

    uv run python -c "from tests.test_golden_hashes import print_hashes; print_hashes()"
"""

import pytest

from questless.config import load_scenario
from questless.sim.world import build_world
from tests.conftest import SCENARIOS

DAYS = 60

GOLDEN = {
    "bandits": "ec6cd83147aa9c9325077be2db75488e15c10f6acc7eecc8dde5f3a83db0cacd",
    "baseline": "635bc82de73f11eb2430864005781c71be7c42de87692103156896acfbd66ca3",
    "drought": "cfa901dfc9c8338b44ab4d3a4c6bc263334a3d266230b3c857cb0a52aaeda1bd",
    "iron_shortage": "d16203bcafa38475e29d9898a1d21a05ba8a7246136732fe17f61d26f6f7fea8",
    "legitimacy_spiral": "e9f9d051d895acda19e89eb084e203b2e2b63da8d45aa3995d4fe2a3577b5df3",
    "mine_disaster": "f2104b1cf8400d0a54568330289311376778249c5a4aef86973b3b40dfc8ba2d",
}


def _hash(name: str) -> str:
    world = build_world(load_scenario(SCENARIOS / f"{name}.toml"))
    world.step(DAYS)
    return world.state_hash()


def print_hashes() -> None:
    for path in sorted(SCENARIOS.glob("*.toml")):
        print(f'    "{path.stem}": "{_hash(path.stem)}",')


def test_every_shipped_scenario_has_a_golden_hash():
    assert {p.stem for p in SCENARIOS.glob("*.toml")} == set(GOLDEN)


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_scenario_reaches_its_golden_state(name):
    assert _hash(name) == GOLDEN[name], (
        f"{name} no longer reaches its pinned state after {DAYS} days. If the change is "
        "deliberate, check `questless diff` and update GOLDEN (see the module docstring)."
    )
