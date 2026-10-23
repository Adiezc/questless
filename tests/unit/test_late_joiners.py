# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M58.2: the late-joiner harness runs, shifts the shock with the join day, and replays exactly."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "experiments"))

from late_joiners import METRICS, run  # noqa: E402


def test_late_joiner_run_reports_every_metric_and_replays():
    first = run("drought", seed=1, join=40, window=45)
    assert set(METRICS) <= set(first)
    assert first["join"] == 40
    assert first["contracts_posted"] > 0  # the shifted shock still lands inside the window
    assert run("drought", seed=1, join=40, window=45) == first
