# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Economic shocks as time-bounded multipliers. Shocks never move goods or coin themselves; they
only change rates (site output, transport capacity), so every effect flows through the ledger."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from questless.config import ShockConfig, ShockEffect
from questless.sim.entities import Site


@dataclass(frozen=True, slots=True)
class Shock:
    name: str
    effect: ShockEffect
    start: int
    end: int  # exclusive
    factor: float
    site: Site | None = None
    source: str = "scenario"  # "scenario" | "user"

    def active(self, tick: int) -> bool:
        return self.start <= tick < self.end

    @classmethod
    def from_config(cls, cfg: ShockConfig) -> Shock:
        return cls(cfg.name, cfg.effect, cfg.start, cfg.start + cfg.duration, cfg.factor, cfg.site)


class Modifiers:
    def __init__(self, shocks: list[Shock] | None = None) -> None:
        self.shocks: list[Shock] = list(shocks or [])

    def add(self, shock: Shock) -> None:
        self.shocks.append(shock)

    def active(self, tick: int) -> list[Shock]:
        return [s for s in self.shocks if s.active(tick)]

    def site_output(self, site: Site, tick: int) -> float:
        factor = 1.0
        for s in self.active(tick):
            if s.effect is ShockEffect.SITE_OUTPUT and s.site is site:
                factor *= s.factor
        return factor

    def transport_capacity(self, tick: int) -> float:
        factor = 1.0
        for s in self.active(tick):
            if s.effect is ShockEffect.TRANSPORT_CAPACITY:
                factor *= s.factor
        return factor

    def state(self) -> list[dict]:
        return [
            {k: str(v) if v is not None else None for k, v in asdict(s).items()}
            for s in self.shocks
        ]
