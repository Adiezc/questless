# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
import dataclasses
import json

import pytest

from questless.cli import main
from questless.config import ConfigError, load_scenario, parse_scenario, to_dict
from tests.conftest import SCENARIOS


@pytest.mark.parametrize(
    "name",
    ["baseline", "iron_shortage", "mine_disaster", "drought", "bandits", "legitimacy_spiral"],
)
def test_shipped_scenarios_load_and_round_trip(name):
    cfg = load_scenario(SCENARIOS / f"{name}.toml")
    assert parse_scenario(to_dict(cfg)) == cfg


def test_guilds_without_max_treasury_round_trip():
    """A guild with no treasury ceiling saves and loads again (#48 made the key optional)."""
    cfg = load_scenario(SCENARIOS / "baseline.toml")
    guilds = {
        gid: dataclasses.replace(g, policy=dataclasses.replace(g.policy, max_treasury=None))
        for gid, g in cfg.guilds.items()
    }
    cfg = dataclasses.replace(cfg, guilds=guilds)
    assert parse_scenario(to_dict(cfg)) == cfg


def test_extends_overrides_only_what_it_sets():
    base = load_scenario(SCENARIOS / "baseline.toml")
    iron = load_scenario(SCENARIOS / "iron_shortage.toml")
    assert iron.name == "Iron Shortage" and len(iron.shocks) == 1
    assert iron.professions == base.professions and iron.seed == base.seed


def test_circular_extends_is_rejected(tmp_path):
    (tmp_path / "a.toml").write_text('[scenario]\nextends = "b.toml"\n')
    (tmp_path / "b.toml").write_text('[scenario]\nextends = "a.toml"\n')
    with pytest.raises(ConfigError, match="circular"):
        load_scenario(tmp_path / "a.toml")


def test_cli_run_prints_contracts_with_provenance(capsys):
    assert main(["run", str(SCENARIOS / "iron_shortage.toml"), "--days", "40"]) == 0
    out = capsys.readouterr().out
    assert "guild_supply" in out and "Mine collapse" in out and "escrowed" in out


def test_cli_json_and_replay(tmp_path, capsys):
    save = tmp_path / "s.json"
    args = ["run", str(SCENARIOS / "drought.toml"), "--days", "40", "--json", "--save", str(save)]
    assert main(args) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["contracts"] and data["contracts"][0]["why"]
    assert main(["replay", str(save)]) == 0
    assert "verified" in capsys.readouterr().out
