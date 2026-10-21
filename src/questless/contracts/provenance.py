# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Quest provenance: the recorded evidence chain that explains why a contract exists.

Every ``Evidence`` item is a measured fact (metric, value, threshold, tick) read from the
simulation's own records, never free text. Human-readable reasons are rendered *from* the chain,
so the UI can only claim what the data shows. Milestone M6 extends the chain back to root causes
(shocks, production drops, price spikes).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Evidence:
    tick: int
    # kind: "shock" | "production_drop" | "price_spike" | "unfilled_demand"
    #       | "inventory_below_target" | "need_persisted" | "guild_emergency"
    #       | "transport_backlog" | "funding_decision"
    kind: str
    subject: str  # "site:mine", "npc_031", "market:iron_ore", "guild:blacksmiths"
    metric: str
    value: float
    threshold: float | None = None
    baseline: float | None = None
    caused_by: tuple[int, ...] = ()  # indexes of earlier evidence in the chain

    def render(self) -> str:
        parts = [f"day {self.tick}: {self.subject} {self.metric} = {_num(self.value)}"]
        if self.baseline is not None:
            parts.append(f"(baseline {_num(self.baseline)})")
        if self.threshold is not None:
            parts.append(f"(threshold {_num(self.threshold)})")
        return " ".join(parts)


@dataclass(frozen=True, slots=True)
class Provenance:
    chain: tuple[Evidence, ...]
    world_hash: str  # state hash on the tick the contract was created
    parent_contract: str | None = None
    notes: tuple[str, ...] = field(default=())

    def render(self) -> list[str]:
        return [e.render() for e in self.chain]


def _num(v: float) -> str:
    return f"{v:.0f}" if float(v).is_integer() else f"{v:.2f}"
