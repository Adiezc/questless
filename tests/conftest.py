# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
import dataclasses
from pathlib import Path

import pytest

from questless.config import ScenarioConfig, ShockConfig, ShockEffect, load_scenario
from questless.sim.entities import Site

SCENARIOS = Path(__file__).resolve().parents[1] / "scenarios"


@pytest.fixture
def baseline() -> ScenarioConfig:
    return load_scenario(SCENARIOS / "baseline.toml")


def with_shocks(cfg: ScenarioConfig, *shocks: ShockConfig) -> ScenarioConfig:
    return dataclasses.replace(cfg, shocks=tuple(shocks))


def mine_collapse(start: int = 20, duration: int = 30, factor: float = 0.2) -> ShockConfig:
    return ShockConfig("Mine collapse", ShockEffect.SITE_OUTPUT, start, duration, factor, Site.MINE)


def drought(start: int = 20, duration: int = 25, factor: float = 0.4) -> ShockConfig:
    return ShockConfig("Drought", ShockEffect.SITE_OUTPUT, start, duration, factor, Site.FARMS)


def bandits(start: int = 20, duration: int = 20, factor: float = 0.3) -> ShockConfig:
    return ShockConfig(
        "Bandits on the road", ShockEffect.TRANSPORT_CAPACITY, start, duration, factor
    )
