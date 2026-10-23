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


# --- M23.5 comment, M23.7 gates, M23.8 determinism, M23.3 command ------------------------------


def _change(metric="hungry_npc_days", base=100.0, head=150.0, significant=True, scenario="drought"):
    from questless.diff import Change

    diff = head - base
    return Change(scenario, metric, base, head, diff, 1.0, diff / base, significant)


def test_comment_says_no_change_when_nothing_moved():
    from questless.diff import MARKER, render_markdown

    text = render_markdown(
        [_change(head=100.0, significant=False)], base_ref="main", seeds=10, scenarios=5
    )
    assert text.startswith(MARKER)
    assert "10 seeds × 5 scenarios, against `main`" in text
    assert "No significant change" in text and "Nothing moved" in text


def test_comment_lists_significant_changes_in_plain_words_biggest_first():
    from questless.diff import render_markdown

    changes = [
        _change("price_index.tools", 1.0, 1.1),
        _change("hungry_npc_days", 100.0, 250.0),
        _change("contracts_posted", 10.0, 10.2, significant=False),
    ]
    text = render_markdown(
        changes, base_ref="main", seeds=3, scenarios=1, problems=["Invariant broken"]
    )
    bullets = [line for line in text.splitlines() if line.startswith("- ")]
    assert bullets[0] == "- Invariant broken"
    assert bullets[1] == "- Hungry NPC-days in Drought: 100 → 250 (**2.5×**)"
    assert bullets[2] == "- Tools price in Drought: 1 → 1.1 (**+10%**)"
    assert "| Drought | Contracts posted | 10 | 10.2 | +2.0% | no |" in text


def test_gates_fail_only_significant_changes_outside_their_limits(tmp_path):
    from questless.diff import check_gates, load_gates

    path = tmp_path / "ci.toml"
    path.write_text(
        '[gates]\n"hungry_npc_days" = { max_ratio = 1.2 }\n'
        '"price_index.*" = { min_ratio = 0.9, max_ratio = 1.2 }\n'
    )
    gates = load_gates(path)
    assert check_gates([_change("hungry_npc_days", 100, 110)], gates) == []
    assert len(check_gates([_change("hungry_npc_days", 100, 130)], gates)) == 1
    assert check_gates([_change("hungry_npc_days", 100, 130, significant=False)], gates) == []
    assert len(check_gates([_change("price_index.food", 1.0, 0.8)], gates)) == 1
    assert load_gates(tmp_path / "missing.toml") == {}
    path.write_text('[gates]\n"x" = { most = 2 }\n')
    with pytest.raises(ValueError, match="max_ratio"):
        load_gates(path)


def _rows(hashes):
    return [
        {"scenario": sc, "seed": 1, "state_hash": h, "failure": None, "metrics": {}}
        for sc, h in hashes.items()
    ]


def test_determinism_flags_hash_changes_only_when_nothing_explains_them():
    from questless.diff import determinism_problems

    root = SCENARIOS.parent
    base = _rows({"drought": "a", "bandits": "b"})
    head = _rows({"drought": "a", "bandits": "CHANGED"})
    assert determinism_problems(base, base, [], SCENARIOS, root) == []
    assert len(determinism_problems(base, head, ["README.md"], SCENARIOS, root)) == 1
    assert determinism_problems(base, head, ["src/questless/sim/world.py"], SCENARIOS, root) == []
    assert determinism_problems(base, head, ["scenarios/bandits.toml"], SCENARIOS, root) == []
    # bandits.toml extends baseline.toml, so changing the parent explains it too
    assert determinism_problems(base, head, ["scenarios/baseline.toml"], SCENARIOS, root) == []


def test_diff_command_against_head_reports_no_change(tmp_path):
    from questless.cli import main

    code = main(
        [
            "diff",
            "--base",
            "HEAD",
            "--seeds",
            "2",
            "--days",
            "20",
            "--workers",
            "1",
            "--out",
            str(tmp_path),
        ]
    )
    assert code == 0
    assert "No significant change" in (tmp_path / "economy-diff.md").read_text()
    import json

    data = json.loads((tmp_path / "economy-diff.json").read_text())
    assert data["problems"] == [] and len(data["head_rows"]) == len(data["base_rows"])
