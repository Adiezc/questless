# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Policy overlays (M52.1): a policy is a scenario file that ``extends`` another and changes only
the rules, never the world.

    [scenario]
    extends = "../../../scenarios/iron_shortage.toml"
    name = "Iron Shortage, progressive levy"

    [[town.levy_brackets]]
    threshold = 500
    rate = 0.06

``load`` returns the base scenario and the policy, ``diff`` lists the knobs that changed, and a
policy that touches anything outside ``RULES`` (goods, professions, shocks, seed, days...) is
rejected: comparing worlds that differ in more than their rules would measure the wrong thing.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from questless.config import ConfigError, ScenarioConfig, load_scenario, to_dict

# Paths a policy may change, as prefixes of the flattened config ("*" matches one guild id).
RULES = (
    "scenario.name",
    "scenario.description",
    "town.",
    "contracts.",
    "legitimacy.",
    "transport.fee_rate",
    "player.caravan_markup",  # an import tariff
    "guilds.*.dues_rate",
    "guilds.*.policy.",
)


class PolicyError(ConfigError):
    pass


def load(path: str | Path) -> tuple[ScenarioConfig, ScenarioConfig]:
    """The scenario a policy extends, and the policy applied to it."""
    path = Path(path)
    with path.open("rb") as fh:
        parent = tomllib.load(fh).get("scenario", {}).get("extends")
    if parent is None:
        raise PolicyError(f"{path}: a policy must extend a scenario ([scenario] extends = ...)")
    base, policy = load_scenario(path.parent / parent), load_scenario(path)
    outside = [k for k in diff(base, policy) if not _is_rule(k)]
    if outside:
        raise PolicyError(f"{path}: a policy may change only the rules, not {', '.join(outside)}")
    return base, policy


def diff(a: ScenarioConfig, b: ScenarioConfig) -> dict[str, tuple[Any, Any]]:
    """Every knob that differs between two configs, as ``{dotted.path: (a's value, b's value)}``.
    Arrays (levy brackets, shocks) compare whole; a missing key reads as ``None``."""
    flat_a, flat_b = _flatten(to_dict(a)), _flatten(to_dict(b))
    return {
        k: (flat_a.get(k), flat_b.get(k))
        for k in sorted(flat_a.keys() | flat_b.keys())
        if flat_a.get(k) != flat_b.get(k)
    }


def _flatten(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in data.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(_flatten(value, f"{path}."))
        else:
            out[path] = value
    return out


def _is_rule(path: str) -> bool:
    parts = path.split(".")
    generic = ".".join("*" if i == 1 and parts[0] == "guilds" else p for i, p in enumerate(parts))
    return any(generic == r or (r.endswith(".") and generic.startswith(r)) for r in RULES)
