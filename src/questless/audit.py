# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Strict provenance checks: rebuild every contract from the scenario and the action log.

``provenance.verify`` re-measures the numbers in a chain against the world's recorded stats. That
catches an edited number, but not an invented cause, an edited decision record (what an NPC went
without, what a funder held) or a rewired chain, because those are read from live state that has
since changed. The world is deterministic, so this module replays the run and compares each
contract, chain and all, with the one the replay posted. A contract passes only if the simulation
would have posted exactly that contract, for exactly those reasons.

    from questless.audit import audit
    problems = audit(world)  # {contract_id: [problem, ...]}; all lists empty when it holds

A replay costs about as much as the run (roughly 2 ms per simulated day at 100 NPCs), so check a
whole world with one ``audit`` call, or reuse one ``rebuild`` for several ``verify_against`` calls.

``but_for`` goes one step further, from "the simulation posted this" to "this shock caused it":
for each shock a contract cites, it replays the run without that shock and checks that the same
need is not posted within a few days of the original.
"""

from __future__ import annotations

import dataclasses
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from questless.config import ScenarioConfig
from questless.contracts.model import Contract, ContractKind
from questless.contracts.provenance import Evidence, verify
from questless.persistence import replay
from questless.player import ActionError, apply_action
from questless.sim.world import World, build_world

# Fields that change after a contract is posted (accept, deliver, abandon, expire). Everything
# else is fixed at posting, so new fields are checked by default.
LIFECYCLE = frozenset({"status", "accepted_by", "closed_tick", "outcome"})


class NotReplayable(RuntimeError):
    """The world doesn't replay from its scenario and action log, so its contracts can't be
    rebuilt. It was changed outside ``apply_action`` (a test moving balances directly, say), or
    built by different code (a dashboard session that survived a reload)."""


def rebuild(world: World) -> World:
    """Replay ``world`` from its scenario and action log to its current tick, and check that the
    replay reaches the same state. Raises ``NotReplayable`` when it doesn't."""
    twin = replay(world.config, world.actions, world.tick)
    if twin.state_hash() != world.state_hash():
        raise NotReplayable(
            "this world does not replay from its scenario and action log, so its contracts "
            "can't be rebuilt"
        )
    return twin


def verify_against(twin: World, contract: Contract) -> list[str]:
    """Differences between ``contract`` and the one with the same id in a replayed ``twin``.
    Empty when the simulation posted exactly this contract."""
    rebuilt = twin.contracts.contracts.get(contract.id)
    if rebuilt is None:
        return [f"{contract.id} was never posted in a replay of this run"]
    problems = []
    for f in dataclasses.fields(Contract):
        if f.name in LIFECYCLE or f.name == "provenance":
            continue
        mine, theirs = getattr(contract, f.name), getattr(rebuilt, f.name)
        if mine != theirs:
            problems.append(f"{f.name}: recorded {mine!r}, rebuilt {theirs!r}")
    problems += _compare_provenance(contract.provenance, rebuilt.provenance)
    return problems


def audit(world: World, twin: World | None = None) -> dict[str, list[str]]:
    """Check every contract in ``world``: re-measure its numbers, then compare it with a replay.
    Returns ``{contract_id: problems}``. Raises ``NotReplayable`` if the world can't be replayed."""
    twin = twin if twin is not None else rebuild(world)
    return {
        cid: verify(world, c) + verify_against(twin, c)
        for cid, c in sorted(world.contracts.contracts.items())
    }


def _compare_provenance(mine, theirs) -> list[str]:
    problems = []
    for i, (a, b) in enumerate(zip(mine.chain, theirs.chain, strict=False)):
        if a != b:
            problems.append(
                f"chain step #{i} ({a.kind}) differs from the rebuilt chain: {_diff(a, b)}"
            )
            break  # later steps are usually shifted copies of the same change
    if len(mine.chain) != len(theirs.chain):
        problems.append(
            f"chain has {len(mine.chain)} steps, the rebuilt chain has {len(theirs.chain)}"
        )
    for name in ("world_hash", "parent_contract", "notes"):
        if getattr(mine, name) != getattr(theirs, name):
            problems.append(f"provenance {name} differs from the rebuilt one")
    return problems


def _diff(a: Evidence, b: Evidence) -> str:
    changed = [
        f"{f.name} {getattr(a, f.name)!r} (rebuilt {getattr(b, f.name)!r})"
        for f in dataclasses.fields(Evidence)
        if getattr(a, f.name) != getattr(b, f.name)
    ]
    return ", ".join(changed)


# --- but-for (counterfactual) checks ------------------------------------------------------------

# Days either side of the original posting within which the same need posting without the shock
# counts as "would have happened anyway". Needs take a few days of patience to post, and a shock
# can bring a need forward without causing it, so an exact-day match would be too strict.
BUT_FOR_WINDOW = 7


@dataclass(frozen=True, slots=True)
class ButFor:
    """The verdict for one shock a contract cites, or for all of them together."""

    shocks: tuple[str, ...]  # one name, or every cited shock for the joint test
    holds: bool  # without these shocks, the need was not posted within the window
    posted_without: int | None  # posting tick of the nearest matching contract without them
    checked_until: int  # last tick the counterfactual covered (shorter if the run ends sooner)
    # Player actions up to checked_until on contracts that don't exist without the shock.
    dropped_actions: int
    # Player actions up to checked_until the counterfactual refused (a caravan the player can no
    # longer afford without those contracts' rewards, say).
    rejected_actions: int
    # True only when the counterfactual differs from the real run by the shock alone: the window
    # fits in the run and every player action up to its end replayed. A player reacts to the
    # world, so what they would have done without the shock is unknowable, and a fixed action
    # log can't stand in for it once it stops applying.
    conclusive: bool


def but_for(
    world: World, contract: Contract, window: int = BUT_FOR_WINDOW, *, twin: World | None = None
) -> list[ButFor]:
    """For each shock ``contract`` cites, replay the run without it and report whether the need
    it serves was posted anyway near the original: a contract for the same good, of the same
    transport-or-supply kind, serving any of the same NPCs (so a guild pool counts for a
    member's own need), posted within ``window`` days or still live when the original was
    posted. ``holds`` is the but-for test: the shock was necessary for this contract, in this run.

    The replay keeps the seed and the player's actions. Contract ids shift once a shock is gone,
    so an action on a contract is applied to the counterfactual contract posted for the same need
    on the same day. When there is none, the shock created that contract and the action is
    dropped; an action the counterfactual refuses is rejected. Either way the player's run has
    diverged, so ``conclusive`` is False, as it is when the run ends before the window does.

    When a contract cites several shocks, a last entry removes them all at once. Two shocks that
    would each have caused the shortage alone both fail the single test (neither was necessary)
    while the joint test still holds (together they were). A contract citing no shock returns
    ``[]``. Raises ``NotReplayable`` (checked with a full replay, unless you pass the replayed
    ``twin`` from ``rebuild``) if the world can't be replayed at all."""
    if twin is None:
        rebuild(world)
    end = min(world.tick, contract.created_tick + window + 1)
    return _judge(world, contract, window, lambda removed: _counterfactual(world, removed, end))


def but_for_all(world: World, window: int = BUT_FOR_WINDOW) -> dict[str, list[ButFor]]:
    """``but_for`` for every contract, replaying each distinct set of removed shocks only once
    (to the world's current tick)."""
    rebuild(world)
    cache: dict[frozenset[int], tuple[World, list[int], list[int]]] = {}

    def replay_without(removed: frozenset[int]) -> tuple[World, list[int], list[int]]:
        if removed not in cache:
            cache[removed] = _counterfactual(world, removed, world.tick)
        return cache[removed]

    return {
        cid: _judge(world, c, window, replay_without)
        for cid, c in sorted(world.contracts.contracts.items())
    }


def _judge(world: World, contract: Contract, window: int, replay_without) -> list[ButFor]:
    cited = _cited_shock_indexes(world, contract)
    tests = [frozenset({i}) for i in cited]
    if len(cited) > 1:
        tests.append(frozenset(cited))
    checked_until = min(world.tick - 1, contract.created_tick + window)
    truncated = checked_until < contract.created_tick + window
    out = []
    for removed in tests:
        twin, dropped_ticks, rejected_ticks = replay_without(removed)
        dropped = sum(t <= checked_until for t in dropped_ticks)
        rejected = sum(t <= checked_until for t in rejected_ticks)
        hits = [
            c.created_tick
            for c in twin.contracts.contracts.values()
            if matches(c, contract, window)
        ]
        nearest = min(hits, key=lambda t: (abs(t - contract.created_tick), t)) if hits else None
        names = tuple(world.modifiers.shocks[i].name for i in sorted(removed))
        conclusive = not truncated and dropped == 0 and rejected == 0
        out.append(ButFor(names, not hits, nearest, checked_until, dropped, rejected, conclusive))
    return out


def matches(candidate: Contract, original: Contract, window: int = BUT_FOR_WINDOW) -> bool:
    """Whether a counterfactual ``candidate`` shows that ``original``'s need was met anyway: it
    serves the same need and was posted within ``window`` days, or earlier and still live."""
    return _serves_same_need(candidate, original) and (
        abs(candidate.created_tick - original.created_tick) <= window
        or _live_at(candidate, original)
    )


def _serves_same_need(candidate: Contract, original: Contract) -> bool:
    return (
        candidate.good == original.good
        and (candidate.kind is ContractKind.TRANSPORT) == (original.kind is ContractKind.TRANSPORT)
        and (
            candidate.dedup_key == original.dedup_key
            or bool(candidate.beneficiaries.keys() & original.beneficiaries.keys())
        )
    )


def _live_at(candidate: Contract, original: Contract) -> bool:
    """Posted earlier and still live when ``original`` was posted, so it would have blocked a
    duplicate posting rather than shown up as one."""
    closed = candidate.closed_tick if candidate.closed_tick is not None else candidate.deadline_tick
    return candidate.created_tick <= original.created_tick < closed


def _cited_shock_indexes(world: World, contract: Contract) -> list[int]:
    indexes = set()
    for ev in contract.provenance.chain:
        if ev.kind == "shock" and ev.measure and ev.measure[0][0] == "shock_factor":
            index = int(ev.measure[0][1])
            if not 0 <= index < len(world.modifiers.shocks):
                raise ValueError(f"{contract.id} cites shock #{index}, which this world lacks")
            indexes.add(index)
    return sorted(indexes)


def _counterfactual(
    world: World, removed: frozenset[int], until: int
) -> tuple[World, list[int], list[int]]:
    config, actions = _without_shocks(world, removed)
    return _replay_lenient(world, config, actions, until)


def _without_shocks(
    world: World, removed: frozenset[int]
) -> tuple[ScenarioConfig, list[dict[str, Any]]]:
    """The scenario and action log without the shocks at ``removed``. The world's shocks are the
    scenario's, in order, followed by those the player added with the ``shock`` action."""
    config = world.config
    n = len(config.shocks)
    kept = tuple(sh for i, sh in enumerate(config.shocks) if i not in removed)
    actions, seen = [], 0
    for entry in world.actions:
        if entry["action"] == "shock":
            seen += 1
            if n + seen - 1 in removed:
                continue
        actions.append(entry)
    return dataclasses.replace(config, shocks=kept), actions


def _replay_lenient(
    real: World, config: ScenarioConfig, actions: list[dict[str, Any]], until: int
) -> tuple[World, list[int], list[int]]:
    """``persistence.replay`` for a counterfactual. Contract ids are sequential, so once a shock
    is gone the same id names a different contract: an action on a contract is redirected to the
    counterfactual contract with the same need posted on the same day. Returns the world and the
    ticks of dropped actions (no such contract) and rejected ones (the world refused them)."""
    world = build_world(config)
    by_tick: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for entry in actions:
        by_tick[entry["tick"]].append(entry)
    dropped: list[int] = []
    rejected: list[int] = []
    for tick in range(until + 1):
        for entry in by_tick.get(tick, []):
            args = dict(entry["args"])
            if "contract_id" in args:
                if args["contract_id"] not in real.contracts.contracts:
                    rejected.append(tick)
                    continue
                match = _counterpart(real, world, args["contract_id"])
                if match is None:
                    dropped.append(tick)
                    continue
                args["contract_id"] = match
            try:
                apply_action(world, entry["action"], **args)
            except ActionError:
                rejected.append(tick)
        if tick < until:
            world.step()
    return world, dropped, rejected


def _counterpart(real: World, twin: World, contract_id: str) -> str | None:
    original = real.contracts.contracts[contract_id]
    for c in twin.contracts.contracts.values():
        if c.dedup_key == original.dedup_key and c.created_tick == original.created_tick:
            return c.id
    return None
