# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Causal walk: explain *why* a good is scarce, back to root causes.

Starting from the contract's good, each step asks the recorded statistics a concrete question:

- Did production of the good fall below its normal level?
  - Gathered goods: was the site hit by a shock? Did more producers than usual work without
    equipment (then: why is equipment scarce? recurse) or go hungry (then: why is food scarce?)
  - Crafted goods: did more crafters than usual sit idle for lack of inputs? (recurse on inputs)
- Was transport capacity cut?
- Did the price spike?

Only facts that pass their threshold become evidence, every measured fact carries its metric key
so it can be re-verified, and the walk is bounded (depth, visited set). Along the way, a recent
contract for an upstream good becomes this contract's *parent*: the quest lineage.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from questless.config import ShockEffect
from questless.contracts.model import ContractKind
from questless.contracts.provenance import Evidence, measure
from questless.sim.entities import Profession, Site
from questless.sim.ledger import Asset

if TYPE_CHECKING:
    from questless.contracts.engine import Candidate
    from questless.sim.world import World

LOOKBACK = 60  # days searched for shocks and parent contracts
BASELINE_DAYS = 30  # length of the "normal" window
RECENT_DAYS = 3  # length of the "now" window
DROP = 0.85  # production below this share of normal counts as a drop
SHARE_RISE = 0.15  # rise in a profession's idle/hungry/broken share that counts
PRICE_SPIKE = 1.25
MAX_DEPTH = 3


@dataclass
class _Walk:
    world: World
    base_tick: int  # end of the "normal" window
    chain: list[Evidence] = field(default_factory=list)
    visited: set[Asset] = field(default_factory=set)
    parent: str | None = None
    exclude_parent: tuple | None = None  # the contract's own need key: a repost is not a parent
    shocks_seen: dict = field(default_factory=dict)  # shock -> evidence index

    def add(self, ev: Evidence) -> int:
        self.chain.append(ev)
        return len(self.chain) - 1


def build_chain(
    world: World, cand: Candidate, extra: list[Evidence]
) -> tuple[list[Evidence], str | None]:
    """Root causes first, then the contract-level facts in ``extra`` (whose ``caused_by`` indexes
    are relative to ``extra`` and get shifted). Returns (chain, parent contract id)."""
    since = min(s.since for s in cand.needs)
    walk = _Walk(world, base_tick=_base_tick(world, since), exclude_parent=cand.key)
    top: list[int] = []
    if cand.kind is ContractKind.TRANSPORT:
        top += _transport_shocks(walk)
    elif walk.base_tick >= RECENT_DAYS:
        if (idx := _explain_scarcity(walk, cand.good, depth=0)) is not None:
            top.append(idx)
        if (idx := _price_spike(walk, cand.good, top)) is not None:
            top = [idx]

    offset = len(walk.chain)
    for i, ev in enumerate(extra):
        caused = tuple(j + offset for j in ev.caused_by) or (tuple(top) if i == 0 else ())
        walk.chain.append(replace(ev, caused_by=caused))
    return walk.chain, walk.parent


def _base_tick(world: World, since: int) -> int:
    """End of the 'normal' window: the day before the need began, or before the earliest shock in
    the lookback window if that came first (so the baseline is not contaminated by the shock)."""
    starts = [s.start for s in world.modifiers.shocks if world.tick - LOOKBACK <= s.start <= since]
    return min([since, *starts]) - 1


def _explain_scarcity(walk: _Walk, good: Asset, depth: int) -> int | None:
    if depth > MAX_DEPTH or good in walk.visited:
        return None
    walk.visited.add(good)
    if depth > 0:
        _note_parent(walk, good)
    world = walk.world
    key = ("produced", str(good), RECENT_DAYS)
    now = measure(world, key, world.tick)
    normal = measure(world, ("produced", str(good), BASELINE_DAYS), walk.base_tick)
    if normal <= 0 or now >= DROP * normal:
        return None

    causes: list[int] = []
    gatherers = [p for p, pc in world.config.professions.items() if good in pc.output]
    crafters = [p for p, pc in world.config.professions.items() if good in pc.recipes]
    for prof in gatherers:
        causes += _site_shocks(walk, prof)
        if world.config.professions[prof].site is not Site.MARKET:
            # Off-market producers pause when their goods cannot reach the market.
            causes += _transport_shocks(walk)
        pc = world.config.professions[prof]
        if pc.equipment is not None:
            idx = _share_rise(walk, prof, "broken", "equipment_shortage", pc.equipment, depth)
            causes += [idx] if idx is not None else []
        idx = _share_rise(walk, prof, "hungry", "hunger", Asset.FOOD, depth)
        causes += [idx] if idx is not None else []
    for prof in crafters:
        inputs = sorted(
            {
                a
                for g, ins in world.config.professions[prof].recipes.items()
                if g == good
                for a in ins
            }
        )
        for upstream in inputs:
            idx = _share_rise(walk, prof, "idle", "input_shortage", upstream, depth)
            causes += [idx] if idx is not None else []

    return walk.add(
        Evidence(
            world.tick,
            "production_drop",
            f"production:{good}",
            "units_per_day",
            now,
            threshold=round(DROP * normal, 2),
            baseline=normal,
            caused_by=tuple(causes),
            measure=(key, world.tick),
            baseline_measure=(("produced", str(good), BASELINE_DAYS), walk.base_tick),
        )
    )


def _share_rise(
    walk: _Walk, prof: Profession, what: str, kind: str, upstream: Asset, depth: int
) -> int | None:
    world = walk.world
    now = measure(world, ("share", str(prof), what, RECENT_DAYS), world.tick)
    normal = measure(world, ("share", str(prof), what, BASELINE_DAYS), walk.base_tick)
    if now - normal < SHARE_RISE:
        return None
    upstream_idx = _explain_scarcity(walk, upstream, depth + 1)
    return walk.add(
        Evidence(
            world.tick,
            kind,
            f"profession:{prof}",
            f"share_{what}",
            now,
            threshold=round(normal + SHARE_RISE, 3),
            baseline=normal,
            caused_by=(upstream_idx,) if upstream_idx is not None else (),
            measure=(("share", str(prof), what, RECENT_DAYS), world.tick),
            baseline_measure=(("share", str(prof), what, BASELINE_DAYS), walk.base_tick),
        )
    )


def _site_shocks(walk: _Walk, prof: Profession) -> list[int]:
    site = walk.world.config.professions[prof].site
    out = []
    for shock in walk.world.modifiers.shocks:
        if (
            shock.effect is ShockEffect.SITE_OUTPUT
            and shock.site is site
            and walk.world.tick - LOOKBACK <= shock.start <= walk.world.tick
        ):
            if shock not in walk.shocks_seen:
                walk.shocks_seen[shock] = walk.add(
                    _shock_evidence(walk, shock, ("site_factor", str(site)))
                )
            out.append(walk.shocks_seen[shock])
    return out


def _transport_shocks(walk: _Walk) -> list[int]:
    out = []
    for shock in walk.world.modifiers.shocks:
        if (
            shock.effect is ShockEffect.TRANSPORT_CAPACITY
            and walk.world.tick - LOOKBACK <= shock.start <= walk.world.tick
        ):
            if shock not in walk.shocks_seen:  # one evidence item per shock, however reached
                walk.shocks_seen[shock] = walk.add(
                    _shock_evidence(walk, shock, ("transport_factor",))
                )
            out.append(walk.shocks_seen[shock])
    return out


def _shock_evidence(walk: _Walk, shock, key: tuple) -> Evidence:
    subject = f"site:{shock.site}" if shock.site else "road:transport"
    return Evidence(
        shock.start,
        "shock",
        subject,
        f"{shock.name.lower().replace(' ', '_')}_factor",
        measure(walk.world, key, shock.start),
        baseline=1.0,
        measure=(key, shock.start),
    )


def _price_spike(walk: _Walk, good: Asset, causes: list[int]) -> int | None:
    world = walk.world
    key = ("price", str(good))
    now = measure(world, key, world.tick)
    before = measure(world, key, walk.base_tick)
    if now < PRICE_SPIKE * before:
        return None
    return walk.add(
        Evidence(
            world.tick,
            "price_spike",
            f"market:{good}",
            "price",
            now,
            threshold=round(PRICE_SPIKE * before, 2),
            baseline=before,
            caused_by=tuple(causes),
            measure=(key, world.tick),
            baseline_measure=(key, walk.base_tick),
        )
    )


def _note_parent(walk: _Walk, upstream: Asset) -> None:
    """The most recent contract for an upstream good becomes the parent (first found wins)."""
    if walk.parent is not None:
        return
    world = walk.world
    recent = [
        c
        for c in world.contracts.contracts.values()
        if c.good is upstream
        and world.tick - LOOKBACK <= c.created_tick < world.tick
        and c.dedup_key != walk.exclude_parent
    ]
    if recent:
        walk.parent = max(recent, key=lambda c: (c.created_tick, c.id)).id
