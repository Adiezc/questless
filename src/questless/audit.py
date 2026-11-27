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
"""

from __future__ import annotations

import dataclasses

from questless.contracts.model import Contract
from questless.contracts.provenance import Evidence, verify
from questless.persistence import replay
from questless.sim.world import World

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
