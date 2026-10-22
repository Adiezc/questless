# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""One-sentence quest summaries, read off the provenance chain.

``summarise`` picks three links: the root cause, the key middle step and the funding, and fills a
short template for each. Like the chain's own rendering, it only repeats numbers the chain
recorded (plus the contract's quantity), so a summary can never claim more than the evidence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from questless.contracts.model import ContractKind
from questless.contracts.provenance import Evidence, _num

if TYPE_CHECKING:
    from questless.contracts.model import Contract
    from questless.sim.world import World

# The middle step that best explains the shortage, in order of preference.
MIDDLE = ("production_drop", "transport_backlog", "price_spike", "unfilled_demand")


def summarise(world: World, contract: Contract) -> str:
    """E.g. "Mine collapse struck on day 15. Iron ore output fell to 5/day from 23.80. The
    Blacksmiths Guild will pay 363 coin for 31 iron ore." """
    chain = contract.provenance.chain
    good = str(contract.good).replace("_", " ")
    parts = []
    root = next((e for e in chain if e.kind == "shock"), None)
    if root is not None:
        name = root.metric.removesuffix("_factor").replace("_", " ")
        parts.append(f"{name.capitalize()} struck on day {root.tick}.")
    middles = [e for kind in MIDDLE for e in chain if e.kind == kind]
    middle = next(
        (e for e in middles if e.subject.partition(":")[2] == str(contract.good)),
        middles[0] if middles else None,
    )
    if middle is not None:
        parts.append(_middle(middle))
    funding = next((e for e in reversed(chain) if e.kind == "funding_decision"), None)
    if funding is not None:
        who = _name(world, contract.funder)
        task = (
            f"to haul {contract.qty} {good} to market"
            if contract.kind is ContractKind.TRANSPORT
            else f"for {contract.qty} {good}"
        )
        parts.append(f"{who} will pay {_num(funding.value)} coin {task}.")
    return " ".join(parts)


def _middle(e: Evidence) -> str:
    good = e.subject.partition(":")[2].replace("_", " ")
    if e.kind == "production_drop":
        return f"{good.capitalize()} output fell to {_num(e.value)}/day from {_num(e.baseline)}."
    if e.kind == "transport_backlog":
        return f"{_num(e.value)} {good} sat waiting at the sites."
    if e.kind == "price_spike":
        return f"The {good} price rose to {_num(e.value)} from {_num(e.baseline)}."
    return f"{_num(e.value)} {good} went unsold to buyers who could pay."


def _name(world: World, account: str) -> str:
    if account == "town":
        return "The town"
    kind, _, gid = account.partition(":")
    if kind == "guild" and gid in world.guilds:
        return f"The {world.guilds[gid].name}"
    npc = world.npcs.get(account)
    return npc.name if npc is not None else account
