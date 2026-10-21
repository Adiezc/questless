# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
from pathlib import Path

import pytest

from questless.config import ScenarioConfig, load_scenario

SCENARIOS = Path(__file__).resolve().parents[1] / "scenarios"


@pytest.fixture
def baseline() -> ScenarioConfig:
    return load_scenario(SCENARIOS / "baseline.toml")
