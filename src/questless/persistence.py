# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Save, load and replay.

The simulation is deterministic, so a save file is tiny: the full scenario, the player's action
log and the tick reached. Loading replays the run and checks the resulting state hash against the
one recorded at save time, so a save also proves that replay is exact.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from questless import __version__
from questless.config import ScenarioConfig, parse_scenario, to_dict
from questless.player import apply_action
from questless.sim.world import World, build_world

FORMAT = "questless-save/1"


class ReplayMismatch(RuntimeError):
    """Replaying the save did not reproduce the recorded state."""


def replay(config: ScenarioConfig, actions: list[dict[str, Any]], until: int) -> World:
    """Build the world and re-run it to tick ``until``, applying each logged action at the tick it
    was originally taken (before that tick's simulation step)."""
    world = build_world(config)
    by_tick: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for entry in actions:
        by_tick[entry["tick"]].append(entry)
    for tick in range(until + 1):
        for entry in by_tick.get(tick, []):
            apply_action(world, entry["action"], **entry["args"])
        if tick < until:
            world.step()
    return world


def to_save(world: World) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "questless_version": __version__,
        "scenario": to_dict(world.config),
        "tick": world.tick,
        "actions": world.actions,
        "state_hash": world.state_hash(),
    }


def save(world: World, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_save(world), indent=2) + "\n")
    return path


def load(path: str | Path) -> World:
    return from_save(json.loads(Path(path).read_text()))


def from_save(data: dict[str, Any]) -> World:
    if data.get("format") != FORMAT:
        raise ValueError(f"not a {FORMAT} file")
    world = replay(parse_scenario(data["scenario"], source="save"), data["actions"], data["tick"])
    if world.state_hash() != data["state_hash"]:
        raise ReplayMismatch(
            "replay did not reproduce the saved state (saved with questless "
            f"{data.get('questless_version')}, running {__version__})"
        )
    return world
