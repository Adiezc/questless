# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M23.1, M23.2, M23.4: metric suite, run grid and paired significance for economy diffs."""

import pytest

from questless.diff import compare, run_grid, significance, suite_metrics
from questless.sim.world import build_world
from tests.conftest import SCENARIOS

BASELINE = str(SCENARIOS / "baseline.toml")
DROUGHT = str(SCENARIOS / "drought.toml")


def test_significance_on_known_data():
    base = [100.0, 102.0, 98.0, 101.0, 99.0]
    assert significance(base, base)[2] is False
    shifted = [b * 1.10 + n for b, n in zip(base, [0.5, -0.5, 0.3, -0.3, 0.0], strict=True)]
    mean, se, significant = significance(base, shifted)
    assert significant and mean == pytest.approx(10.0, abs=0.5) and se > 0
    tiny = [b + 1.0 for b in base]  # consistent, but only 1%: below the minimum effect
    assert significance(base, tiny)[2] is False
    noisy = [b + n for b, n in zip(base, [9.0, -8.0, 7.0, -9.0, 4.0], strict=True)]
    assert significance(base, noisy)[2] is False  # within seed-to-seed noise
    with pytest.raises(ValueError):
        significance(base, base[:3])


def test_suite_metrics_cover_every_good_and_sector(baseline):
    world = build_world(baseline)
    world.step(40)
    m = suite_metrics(world)
    for good in ("food", "iron_ore", "tools", "weapons"):
        assert f"price_index.{good}" in m and f"shortage_days.{good}" in m
    assert m["recovery_days"] == 0  # no shocks
    assert {"hungry_npc_days", "contracts_posted", "contracts_delivered"} <= set(m)
    assert {"coin.town", "coin.guilds", "coin.npcs", "coin.escrow"} <= set(m)


def test_grid_is_the_same_in_one_process_or_several():
    serial = run_grid([BASELINE, DROUGHT], [1, 2], days=30, workers=1)
    parallel = run_grid([BASELINE, DROUGHT], [1, 2], days=30, workers=2)
    assert serial == parallel
    assert [(r["scenario"], r["seed"]) for r in serial] == [
        ("baseline", 1),
        ("baseline", 2),
        ("drought", 1),
        ("drought", 2),
    ]
    assert all(r["metrics"]["invariant_failures"] == 0 for r in serial)


def test_identical_trees_report_no_significant_change():
    grid = run_grid([DROUGHT], [1, 2, 3], days=60)
    assert not [c for c in compare(grid, grid) if c.significant]


def test_halving_farm_output_is_flagged_on_hunger(tmp_path):
    head = tmp_path / "drought.toml"
    head.write_text(
        f'[scenario]\nextends = "{DROUGHT}"\n\n[professions.farmer]\noutput = {{ food = 1.65 }}\n'
    )
    base = run_grid([DROUGHT], [1, 2, 3, 4], days=60)
    changed = run_grid([head], [1, 2, 3, 4], days=60)
    hunger = next(c for c in compare(base, changed) if c.metric == "hungry_npc_days")
    assert hunger.significant and hunger.mean_diff > 0, hunger
