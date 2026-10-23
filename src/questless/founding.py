# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Civilization DNA (M54): a colony inherits its parent's institutions with small changes.

``mutate`` copies a scenario and nudges only the knobs listed in ``[founding.bounds]``, each by at
most ``step`` of its range and never outside it. The result goes back through the strict loader,
so a colony's config is as valid as any hand-written scenario. Draws come from the caller's RNG
(the world's ``founding`` stream), in sorted knob order, so a run replays to the same colonies.
"""

from __future__ import annotations

import copy
import random
from typing import Any

from questless.config import ScenarioConfig, parse_scenario, to_dict

STEP = 0.25  # largest change per founding, as a share of the knob's allowed range


def mutate(cfg: ScenarioConfig, rng: random.Random, step: float = STEP) -> ScenarioConfig:
    """A colony's config: ``cfg`` with each knob in ``cfg.founding_bounds`` moved by up to
    ``step`` × (high − low), clamped to its bounds. Integer knobs stay integers."""
    data = to_dict(cfg)
    for knob, low, high in cfg.founding_bounds:
        for path in _expand(knob, data):
            parent, key = _locate(data, path)
            old = parent[key]
            new = min(max(old + rng.uniform(-1.0, 1.0) * step * (high - low), low), high)
            parent[key] = round(new) if isinstance(old, int) else round(new, 4)
    return parse_scenario(data, source="<colony>")


def mutations(parent: ScenarioConfig, child: ScenarioConfig) -> dict[str, tuple[Any, Any]]:
    """The knobs a colony changed, as ``{path: (parent value, child value)}`` (its lineage diff)."""
    a, b = to_dict(parent), to_dict(child)
    out = {}
    for knob, _, _ in parent.founding_bounds:
        for path in _expand(knob, a):
            old, new = _get(a, path), _get(b, path)
            if old != new:
                out[".".join(path)] = (old, new)
    return out


def _expand(knob: str, data: dict[str, Any]) -> list[tuple[str, ...]]:
    """``guilds.*.dues_rate`` becomes one path per guild, in sorted id order."""
    parts = tuple(knob.split("."))
    if parts[0] == "guilds" and parts[1] == "*":
        return [("guilds", gid, *parts[2:]) for gid in sorted(data["guilds"])]
    return [parts]


def _locate(data: dict[str, Any], path: tuple[str, ...]) -> tuple[dict[str, Any], str]:
    node = data
    for part in path[:-1]:
        node = node[part]
    return node, path[-1]


def _get(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    parent, key = _locate(data, path)
    return copy.deepcopy(parent[key])
