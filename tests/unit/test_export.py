# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Research export: tables that reproduce, add up, leave the run untouched, and are documented."""

import csv
import subprocess
import sys
from pathlib import Path

import pytest

from questless import export
from questless.api import Simulation
from questless.cli import main
from questless.config import ConfigError
from questless.sim.ledger import Asset
from tests.conftest import SCENARIOS

ROOT = Path(__file__).resolve().parents[2]
LEVY = ROOT / "experiments" / "stress" / "policies" / "progressive_levy.toml"
IRON = SCENARIOS / "iron_shortage.toml"
DAYS = 25


@pytest.fixture(scope="module")
def tables(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("export")
    export.export(IRON, out, seeds=[1, 2], policies=[LEVY], days=DAYS)
    return out


def _rows(folder: Path, name: str) -> list[dict[str, str]]:
    with (folder / name).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_same_arms_and_seeds_give_identical_files(tables, tmp_path):
    export.export(IRON, tmp_path, seeds=[1, 2], policies=[LEVY], days=DAYS)
    for name in ("daily.csv", "npc_days.csv", "events.csv", "runs.csv", "codebook.md"):
        assert (tmp_path / name).read_bytes() == (tables / name).read_bytes(), name


def test_exporting_leaves_the_run_exactly_as_a_plain_run(tables):
    for row in _rows(tables, "runs.csv"):
        cfg = export.arms(IRON, [LEVY])[row["arm"] != "base"].config
        sim = Simulation.from_scenario(cfg, seed=int(row["seed"]))
        sim.step(DAYS)
        assert row["state_hash"] == sim.world.state_hash(), (row["arm"], row["seed"])


def test_npc_rows_add_up_to_the_town(tables):
    daily = _rows(tables, "daily.csv")
    npc_days = _rows(tables, "npc_days.csv")
    assert len(daily) == 2 * 2 * DAYS
    coin: dict[tuple[str, str, str], int] = {}
    for r in npc_days:
        key = (r["arm"], r["seed"], r["day"])
        coin[key] = coin.get(key, 0) + int(r["coin"])
        assert float(r["wealth"]) == pytest.approx(
            int(r["coin"]) + float(r["goods_value"]), abs=0.02
        )
    for d in daily:
        assert int(d["npc_coin"]) == coin[d["arm"], d["seed"], d["day"]]
        assert 0 <= float(d["coin_gini"]) <= 1


def test_coin_change_chains_day_to_day(tables):
    sim = Simulation.from_scenario(IRON, seed=1)
    genesis = sim.world.ledger.balance("npc_000", Asset.COIN)
    mine = [
        r
        for r in _rows(tables, "npc_days.csv")
        if (r["arm"], r["seed"], r["npc_id"]) == ("base", "1", "npc_000")
    ]
    assert int(mine[0]["coin"]) - int(mine[0]["coin_change"]) == genesis
    for before, after in zip(mine, mine[1:], strict=False):
        assert int(after["coin"]) - int(after["coin_change"]) == int(before["coin"])


def test_events_list_shocks_and_the_rules_each_arm_changed(tables):
    events = _rows(tables, "events.csv")
    shocks = [e for e in events if e["kind"] == "shock"]
    assert {e["name"] for e in shocks} == {"Mine collapse"}
    assert len(shocks) == 4  # 2 arms × 2 seeds
    policies = [e for e in events if e["kind"] == "policy"]
    assert {e["name"] for e in policies} == {"town.levy_brackets"}
    assert {e["arm"] for e in policies} == {"progressive_levy"}


def test_a_policy_for_another_scenario_is_rejected():
    with pytest.raises(ConfigError, match="different scenario"):
        export.arms(SCENARIOS / "baseline.toml", [LEVY])


def test_codebook_documents_every_column(tables):
    codebook = (tables / "codebook.md").read_text(encoding="utf-8")
    documented: dict[str, set[str]] = {}
    for table, columns in export.COLUMNS.items():
        names = {n.strip() for key in columns for n in key.replace(" / ", ", ").split(",")}
        documented[table] = names
        assert f"## {table}" in codebook
    goods = [str(g) for g in export.GOODS]
    for table in ("daily.csv", "npc_days.csv", "events.csv", "runs.csv"):
        with (tables / table).open(encoding="utf-8") as fh:
            header = next(csv.reader(fh))
        for col in header:
            generic = next((col.replace(g, "<good>") for g in goods if col.endswith(f"_{g}")), col)
            assert generic in documented[table], f"{table}: {col} is not in the codebook"


@pytest.mark.parametrize(
    ("text", "seeds"),
    [("3", [1, 2, 3]), ("5-7", [5, 6, 7]), ("3,7,11", [3, 7, 11]), ("1-2,2,9", [1, 2, 9])],
)
def test_parse_seeds(text, seeds):
    assert export.parse_seeds(text) == seeds


def test_cli_writes_the_tables(tmp_path, capsys):
    assert main(["export", str(IRON), "--seeds", "1", "--days", "3", "--out", str(tmp_path)]) == 0
    assert "npc_days.csv" in capsys.readouterr().out
    assert len(_rows(tmp_path, "runs.csv")) == 1
    assert main(["export", str(IRON), "--seeds", "x", "--out", str(tmp_path)]) == 2


def test_worked_example_runs_on_an_export(tables):
    script = ROOT / "experiments" / "analyse_export.py"
    result = subprocess.run(
        [sys.executable, str(script), str(tables)], capture_output=True, text=True, check=True
    )
    assert "progressive_levy minus base" in result.stdout
