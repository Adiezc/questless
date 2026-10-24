# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""M52.1 and M52.3: policies change only the rules of the scenario they extend, and the hunt
flags an attacker only when it wins on most seeds after the policy but not before."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "experiments" / "stress"))

from hunt import HONEST, PLAYERS, summarise_policy  # noqa: E402

from questless import policy  # noqa: E402

LEVY = ROOT / "experiments" / "stress" / "policies" / "progressive_levy.toml"


def _policy(tmp_path, body, extends=True, scenario=""):
    path = tmp_path / "p.toml"
    parent = ROOT / "scenarios" / "iron_shortage.toml"
    head = f'[scenario]\nextends = "{parent}"\n{scenario}\n' if extends else ""
    path.write_text(head + body)
    return path


def test_diff_lists_only_the_changed_knobs():
    base, pol = policy.load(LEVY)
    changes = policy.diff(base, pol)
    assert set(changes) == {"scenario.name", "town.levy_brackets"}
    assert changes["town.levy_brackets"][0] is None
    assert policy.diff(base, base) == {}


def test_guild_knobs_count_as_rules(tmp_path):
    path = _policy(tmp_path, "[guilds.miners]\ndues_rate = 0.08\n")
    base, pol = policy.load(path)
    assert policy.diff(base, pol) == {"guilds.miners.dues_rate": (0.05, 0.08)}


@pytest.mark.parametrize(
    "scenario, body, where",
    [
        ("seed = 9", "", "scenario.seed"),
        ("", "[professions.miner]\ncount = 1\n", "professions.miner.count"),
        ("", "[guilds.miners]\ntreasury = 9000\n", "guilds.miners.treasury"),
    ],
)
def test_a_policy_cannot_change_the_world(tmp_path, scenario, body, where):
    with pytest.raises(policy.PolicyError, match=where):
        policy.load(_policy(tmp_path, body, scenario=scenario))


def test_a_policy_must_extend_a_scenario(tmp_path):
    with pytest.raises(policy.PolicyError, match="must extend"):
        policy.load(_policy(tmp_path, "[town]\nguard_wage = 6\n", extends=False))


def _rows(gains_before, gains_after, seeds=4):
    """Synthetic hunt rows: honest players earn 4/day; each attacker earns the given amount."""
    rows = []
    for side, gains in (("before", gains_before), ("after", gains_after)):
        for p in PLAYERS:
            for s in range(1, seeds + 1):
                rows.append(
                    {
                        "scenario": f"{side}:{LEVY}",
                        "player": p,
                        "seed": s,
                        "gain_per_day": 4.0 if p in HONEST else gains.get(p, 0.0),
                        "hungry_npc_days": 100,
                    }
                )
    return rows


def test_only_an_exploit_the_policy_opened_is_flagged():
    report = summarise_policy(_rows({"hoarder": 9.0}, {"hoarder": 9.0, "squatter": 9.0}), LEVY)
    assert "New exploits: squatter." in report  # wins only after the policy
    assert "| hoarder |" in report and "4/4 |" in report  # already won before: not new
    clean = summarise_policy(_rows({}, {}), LEVY)
    assert "No new exploit" in clean
