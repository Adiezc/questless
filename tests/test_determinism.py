# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""T8: same scenario + same seed + same actions -> identical state, even across processes with
different hash randomisation (a common hidden source of non-determinism in Python)."""

import os
import subprocess
import sys

from questless.api import Simulation
from tests.conftest import SCENARIOS

SCRIPT = """
from questless.api import Simulation
sim = Simulation.from_scenario({path!r})
sim.step(30)
cid = sim.contracts()[0].id
sim.accept(cid)
sim.caravan("iron_ore", 5)
sim.step(40)
print(sim.world.state_hash())
"""


def _hash_in_subprocess(hash_seed: str) -> str:
    env = {**os.environ, "PYTHONHASHSEED": hash_seed}
    code = SCRIPT.format(path=str(SCENARIOS / "iron_shortage.toml"))
    out = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def test_identical_across_processes_and_hash_seeds():
    hashes = {_hash_in_subprocess(seed) for seed in ("0", "1", "12345")}
    assert len(hashes) == 1


def test_different_seeds_diverge():
    a = Simulation.from_scenario(SCENARIOS / "baseline.toml", seed=1)
    b = Simulation.from_scenario(SCENARIOS / "baseline.toml", seed=2)
    a.step(10)
    b.step(10)
    assert a.world.state_hash() != b.world.state_hash()
