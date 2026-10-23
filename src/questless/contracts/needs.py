# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Need tracking: which shortfalls are persistent *scarcity*, as opposed to noise or poverty.

An NPC has a scarcity day for a good when, on the same day, it
  1. could not do something it needed to (eat, replace equipment, craft): ``unmet > 0``, and
  2. bid for the good at market, could pay, and got nothing: ``unfilled > 0``.
A need becomes *persistent* after ``traits.patience`` scarcity days in a streak; a streak survives
gaps of up to ``gap_tolerance`` calm days, so a lucky purchase does not reset a real shortage.
Days where the NPC simply could not afford the good are counted as poverty, never as scarcity.

Transport needs are tracked per good: goods piling up at production sites while buyers at the
market go unfilled.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from questless.sim.ledger import GOODS, Asset

if TYPE_CHECKING:
    from questless.sim.world import World

TRANSPORT = "transport"


@dataclass(slots=True)
class NeedState:
    subject: str  # NPC id, or TRANSPORT
    good: Asset
    since: int  # first tick of the current streak
    days: int = 0  # consecutive scarcity days
    unmet: int = 0  # latest day's figures
    unfilled: int = 0
    calm_days: int = 0  # consecutive days without scarcity since the streak ended
    trace: list[tuple[int, int, int]] = field(default_factory=list)  # (tick, unmet, unfilled)

    @property
    def active(self) -> bool:
        return self.calm_days == 0


@dataclass(slots=True)
class NeedTracker:
    states: dict[tuple[str, Asset], NeedState] = field(default_factory=dict)
    poverty_days: Counter[Asset] = field(default_factory=Counter)  # NPC-days, today
    forget_after: int = 10  # drop a calm need after this many days
    gap_tolerance: int = 1  # calm days a streak survives

    def update(self, world: World) -> None:
        self.poverty_days = Counter()
        today: dict[tuple[str, Asset], tuple[int, int]] = {}
        for npc in world.npcs_in_order():
            rec = npc.history[-1]
            for good in GOODS:
                unmet, unfilled = rec.unmet.get(good, 0), rec.unfilled.get(good, 0)
                if unmet and unfilled:
                    today[(npc.id, good)] = (unmet, unfilled)
                elif unmet and rec.unaffordable.get(good, 0):
                    self.poverty_days[good] += 1
        for good, (backlog, unfilled) in _transport_signals(world).items():
            today[(TRANSPORT, good)] = (backlog, unfilled)

        for key in sorted(set(self.states) | set(today)):
            state = self.states.get(key)
            if key in today:
                unmet, unfilled = today[key]
                if state is None or state.calm_days > self.gap_tolerance:
                    state = self.states[key] = NeedState(key[0], key[1], since=world.tick)
                state.calm_days = 0
                state.days += 1
                state.unmet, state.unfilled = unmet, unfilled
                state.trace.append((world.tick, unmet, unfilled))
                del state.trace[:-30]
            elif state is not None:
                state.calm_days += 1
                if state.calm_days > self.forget_after:
                    del self.states[key]

    def persistent(self, world: World) -> list[NeedState]:
        """Active needs whose streak has outlasted the subject's patience, in a stable order."""
        out = []
        for (subject, _good), state in sorted(self.states.items()):
            if not state.active:
                continue
            patience = 2 if subject == TRANSPORT else world.npcs[subject].traits.patience
            if state.days >= patience:
                out.append(state)
        return out

    def active_for(self, subjects: list[str], good: Asset) -> list[NeedState]:
        """Needs for ``good`` currently in a scarcity streak (any length) among ``subjects``."""
        found = (self.states.get((s, good)) for s in sorted(subjects))
        return [s for s in found if s is not None and s.active]

    def get(self, subject: str, good: Asset) -> NeedState | None:
        return self.states.get((subject, good))

    def calm_days(self, subject: str, good: Asset) -> int:
        """Days the need has been gone; large if it no longer exists at all."""
        state = self.states.get((subject, good))
        return state.calm_days if state else self.forget_after + 1


def _transport_signals(world: World) -> dict[Asset, tuple[int, int]]:
    """Goods with a site backlog above the threshold while market buyers go unfilled."""
    stats = world.stats[-1]
    threshold = world.config.contracts.transport_backlog_days
    out: dict[Asset, tuple[int, int]] = {}
    for good in GOODS:
        unfilled = stats.market[good].unfilled if good in stats.market else 0
        if not unfilled:
            continue
        daily_output = sum(c.get(good, 0) for c in stats.produced_by_site.values()) or 1
        backlog = sum(
            world.ledger.balance(n.site_account, good)
            for n in world.npcs_in_order()
            if n.site_account != n.account
        )
        if backlog > threshold * daily_output:
            out[good] = (backlog, unfilled)
    return out


def suppressed(world: World) -> dict[str, dict[str, int]]:
    """Needs that did not post as contracts, grouped by suppression reason and poverty."""
    counts: dict[str, int] = {}
    for s in world.stats:
        if s.contracts and s.contracts.suppressed:
            for k, v in s.contracts.suppressed.items():
                counts[k] = counts.get(k, 0) + v

    poverty: dict[str, int] = {}
    if world.stats:
        last_market = world.stats[-1].market
        for good, report in last_market.items():
            if report.unaffordable > 0:
                poverty[str(good)] = report.unaffordable

    return {"counts": counts, "poverty": poverty}
