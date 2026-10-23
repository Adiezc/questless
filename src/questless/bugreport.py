# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Bug reports that replay themselves (M28.1, M28.2).

A bug report is a save file plus what the reporter saw, written as a machine-checkable
**observation**: a metric key that ``provenance.measure`` understands, a day, an operator and a
value. Reproducing it is then a function call (``repro``), not a conversation:

    {"metric": ["price", "tools"], "tick": 74, "op": ">=", "value": 60.0}
"""

from __future__ import annotations

import operator
import platform
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from questless import __version__
from questless.config import parse_scenario
from questless.contracts.provenance import METRICS, measure
from questless.persistence import replay, to_save

if TYPE_CHECKING:
    from questless.sim.world import World

FORMAT = "questless-bug/1"
OPS = {
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
    "==": operator.eq,
    "!=": operator.ne,
}
REPRODUCED, NOT_REPRODUCED, REPLAY_MISMATCH, NO_OBSERVATION = (
    "reproduced",
    "not reproduced",
    "replay mismatch",
    "no observation",
)


@dataclass(frozen=True)
class Outcome:
    status: str  # one of the four constants above
    value: float | None = None  # the observed metric on replay, when there is one
    message: str = ""


def write(world: World, note: str, observation: dict[str, Any] | None = None) -> dict[str, Any]:
    """A bug report for ``world`` as it is now. The observation is checked and evaluated here, so
    a report can't carry a metric or day that ``repro`` would fail to read."""
    if observation is not None:
        _evaluate(world, observation)
    return {
        "format": FORMAT,
        "save": to_save(world),
        "environment": {
            "questless": __version__,
            "python": platform.python_version(),
            "os": sys.platform,
        },
        "note": note,
        "observation": observation,
    }


def repro(report: dict[str, Any]) -> Outcome:
    """Replay the report's save and check its observation against the replayed world."""
    if report.get("format") != FORMAT:
        raise ValueError(f"not a {FORMAT} file")
    save = report["save"]
    world = replay(
        parse_scenario(save["scenario"], source="bug report"), save["actions"], save["tick"]
    )
    if world.state_hash() != save["state_hash"]:
        reported = report.get("environment", {}).get("questless", "?")
        return Outcome(
            REPLAY_MISMATCH,
            message=f"the engine changed since the report (reported on {reported}, "
            f"running {__version__}); replay it with the reporter's version",
        )
    observation = report.get("observation")
    if observation is None:
        return Outcome(NO_OBSERVATION, message="replayed exactly; nothing to check")
    holds, value = _evaluate(world, observation)
    status = REPRODUCED if holds else NOT_REPRODUCED
    return Outcome(status, value, f"{_describe(observation)}: measured {value}")


def _evaluate(world: World, observation: dict[str, Any]) -> tuple[bool, float]:
    metric, tick = observation["metric"], observation["tick"]
    op, expected = observation["op"], observation["value"]
    if not isinstance(metric, list) or not metric or metric[0] not in METRICS:
        raise ValueError(f"unknown metric {metric!r}; known: {sorted(METRICS)}")
    if op not in OPS:
        raise ValueError(f"unknown operator {op!r}; use one of {sorted(OPS)}")
    if not isinstance(tick, int) or not 0 <= tick < len(world.stats):
        raise ValueError(f"day {tick!r} isn't recorded (0-{len(world.stats) - 1})")
    value = measure(world, tuple(metric), tick)
    return OPS[op](value, expected), value


def _describe(observation: dict[str, Any]) -> str:
    metric = " ".join(str(m) for m in observation["metric"])
    return f"{metric} on day {observation['tick']} {observation['op']} {observation['value']}"
