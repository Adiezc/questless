# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Quest provenance: the recorded evidence chain that explains why a contract exists.

Every ``Evidence`` item is a fact read from the simulation's own records. Items that come from
recorded statistics carry a ``measure``: a key into ``METRICS`` plus the tick it was read at, so
``verify`` can recompute the value later and prove the explanation was not made up. Decision
records (a need's streak length, a funding decision) are written at the moment the decision is
made and have no ``measure``.

Human-readable text is rendered *from* the chain, so the UI can only claim what the data shows.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from statistics import fmean
from typing import TYPE_CHECKING

from questless.sim.entities import Profession, Site
from questless.sim.ledger import Asset

if TYPE_CHECKING:
    from questless.contracts.model import Contract
    from questless.sim.world import World

Measure = tuple[tuple, int]  # (metric key, tick)


@dataclass(frozen=True, slots=True)
class Evidence:
    tick: int
    # kind: "shock" | "production_drop" | "equipment_shortage" | "input_shortage" | "hunger"
    #       | "price_spike" | "unfilled_demand" | "need_persisted" | "guild_emergency"
    #       | "town_emergency" | "transport_backlog" | "partial_funding" | "funding_decision"
    kind: str
    subject: str  # "site:mine", "npc_031", "market:iron_ore", "guild:blacksmiths"
    metric: str
    value: float
    threshold: float | None = None
    baseline: float | None = None
    caused_by: tuple[int, ...] = ()  # indexes of earlier evidence in the chain
    measure: Measure | None = None  # how to recompute ``value``
    baseline_measure: Measure | None = None  # how to recompute ``baseline``

    def render(self, names: dict[str, str] | None = None) -> str:
        """One sentence. ``names`` maps NPC ids to display names."""
        text = TEMPLATES.get(self.kind, "{subject} {metric} = {value}")
        return f"Day {self.tick}: " + text.format(
            subject=(names or {}).get(self.subject) or _label(self.subject),
            metric=self.metric.replace("_", " "),
            value=_num(self.value),
            baseline=_num(self.baseline) if self.baseline is not None else "?",
            threshold=_num(self.threshold) if self.threshold is not None else "?",
            pct=_pct(self.value),
            base_pct=_pct(self.baseline) if self.baseline is not None else "?",
            thr_pct=_pct(self.threshold) if self.threshold is not None else "?",
        )


@dataclass(frozen=True, slots=True)
class Provenance:
    chain: tuple[Evidence, ...]
    world_hash: str  # state hash on the tick the contract was created
    parent_contract: str | None = None
    notes: tuple[str, ...] = field(default=())

    def render(self, names: dict[str, str] | None = None) -> list[str]:
        return [e.render(names) for e in self.chain]

    def roots(self) -> list[Evidence]:
        return [e for e in self.chain if not e.caused_by]


TEMPLATES = {
    "shock": "{subject}: {metric} set to {value} by an external shock.",
    "production_drop": "{subject} output fell to {value}/day (normal {baseline}/day).",
    "equipment_shortage": (
        "{pct} of {subject} worked without usable equipment (normally {base_pct})."
    ),
    "input_shortage": "{pct} of {subject} sat idle for lack of inputs (normally {base_pct}).",
    "hunger": "{pct} of {subject} went hungry (normally {base_pct}).",
    "price_spike": "{subject} price rose to {value} (was {baseline}).",
    "unfilled_demand": "{subject}: {value} units wanted by buyers who could pay went unsold.",
    "need_persisted": "{subject} went {value} {metric} (patience {threshold} days).",
    "guild_emergency": "{subject}: {pct} of members who use it are short (emergency at {thr_pct}).",
    "town_emergency": "{subject}: {pct} of guards are short (emergency at {thr_pct}).",
    "transport_backlog": "{subject}: {value} units waiting at production sites.",
    "partial_funding": "{subject} could fund {value} of the {threshold} units needed.",
    "funding_decision": "{subject} escrowed {value} coin (had {baseline}, limit {threshold}).",
}


# --- metrics ------------------------------------------------------------------------------------


def _window(world: World, tick: int, days: int) -> list:
    return world.stats[max(tick - days + 1, 0) : tick + 1]


def _produced(world: World, tick: int, good: str, days: int) -> float:
    return round(fmean(s.produced.get(Asset(good), 0) for s in _window(world, tick, days)), 2)


def _share(world: World, tick: int, profession: str, what: str, days: int) -> float:
    values = []
    for s in _window(world, tick, days):
        counts = s.by_profession.get(Profession(profession))
        if counts and counts["count"]:
            values.append(counts[what] / counts["count"])
    return round(fmean(values), 3) if values else 0.0


METRICS: dict[str, Callable[..., float]] = {
    "unfilled": lambda w, t, good: w.stats[t].market[Asset(good)].unfilled,
    "price": lambda w, t, good: round(w.stats[t].prices[Asset(good)], 2),
    "produced": _produced,
    "share": _share,
    "site_factor": lambda w, t, site: w.modifiers.site_output(Site(site), t),
    "transport_factor": lambda w, t: w.modifiers.transport_capacity(t),
}


def measure(world: World, key: tuple, tick: int) -> float:
    name, *args = key
    return METRICS[name](world, tick, *args)


def verify(world: World, contract: Contract) -> list[str]:
    """Recompute every measured evidence value and check the chain's structure.
    Returns a list of problems (empty when the provenance holds)."""
    problems = []
    for i, ev in enumerate(contract.provenance.chain):
        if ev.tick > contract.created_tick:
            problems.append(f"#{i} {ev.kind} is dated after the contract")
        if any(j >= i for j in ev.caused_by):
            problems.append(f"#{i} {ev.kind} is caused by later evidence")
        for recorded, m in ((ev.value, ev.measure), (ev.baseline, ev.baseline_measure)):
            if m is not None:
                actual = measure(world, *m)
                if not math.isclose(actual, recorded, rel_tol=1e-9, abs_tol=1e-9):
                    problems.append(f"#{i} {ev.kind}: recorded {recorded}, measured {actual}")
    return problems


# --- rendering ----------------------------------------------------------------------------------


def _label(subject: str) -> str:
    kind, _, name = subject.partition(":")
    name = name.replace("_", " ")
    return {
        "site": f"The {name}",
        "market": f"Market for {name}",
        "production": f"{name.capitalize()} production",
        "profession": f"{name}s",
        "guild": f"{name.capitalize()} Guild",
        "sites": f"Sites ({name})",
        "road": "The road",
    }.get(kind, subject.capitalize() if subject == "town" else subject)


def _num(v: float) -> str:
    return f"{v:.0f}" if float(v).is_integer() else f"{v:.2f}"


def _pct(v: float | None) -> str:
    return f"{v * 100:.0f}%" if v is not None else "?"
