# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Public Python API: one object to run a world, act as the player and inspect what happened.

    from questless import Simulation

    sim = Simulation.from_scenario("scenarios/iron_shortage.toml")
    sim.run_until_contract()
    c = sim.contracts(status="open")[0]
    print(c.reason)
    print("\\n".join(sim.explain(c.id)))
    sim.accept(c.id)
    sim.caravan(str(c.good), c.qty)
    sim.step(sim.config.contracts.caravan_days)
    sim.deliver(c.id)

Everything that changes the world goes through the action log, so ``save``/``load`` and replay
reproduce a session exactly. The returned contract and entity objects are live views: read them,
don't mutate them.
"""

from __future__ import annotations

import dataclasses
from collections import Counter
from pathlib import Path
from typing import Any

from questless import bugreport, persistence
from questless.config import ScenarioConfig, load_scenario
from questless.contracts import causes
from questless.contracts.model import Contract, Status
from questless.contracts.provenance import series, verify
from questless.contracts.summary import summarise
from questless.metrics import timeseries
from questless.player import Quote, apply_action, quote_contract
from questless.sim.entities import PLAYER
from questless.sim.ledger import GOODS, Asset
from questless.sim.world import World, build_world


class UnknownIdError(KeyError):
    def __str__(self) -> str:
        return str(self.args[0])


class Simulation:
    def __init__(self, world: World) -> None:
        self.world = world

    # --- construction ---------------------------------------------------------------------------

    @classmethod
    def from_scenario(
        cls, scenario: str | Path | ScenarioConfig, *, seed: int | None = None
    ) -> Simulation:
        cfg = scenario if isinstance(scenario, ScenarioConfig) else load_scenario(scenario)
        if seed is not None:
            cfg = dataclasses.replace(cfg, seed=seed)
        return cls(build_world(cfg))

    @classmethod
    def load(cls, path: str | Path) -> Simulation:
        return cls(persistence.load(path))

    def save(self, path: str | Path) -> Path:
        return persistence.save(self.world, path)

    def bug_report(self, note: str, observation: dict[str, Any] | None = None) -> dict[str, Any]:
        """A self-replaying bug report: this run's save, plus what you saw as a checkable
        observation such as ``{"metric": ["price", "tools"], "tick": 74, "op": ">=",
        "value": 60}``. Check it later with ``questless repro``."""
        return bugreport.write(self.world, note, observation)

    # --- time -----------------------------------------------------------------------------------

    @property
    def config(self) -> ScenarioConfig:
        return self.world.config

    @property
    def day(self) -> int:
        return self.world.tick

    def step(self, days: int = 1) -> list[str]:
        """Advance ``days``; returns the ids of contracts posted meanwhile."""
        created: list[str] = []
        if days < 0:
            raise ValueError("Days must be non-negative")

        for _ in range(days):
            self.world.step()
            created += self.world.stats[-1].contracts.created
        return created

    def run_until_contract(self, max_days: int = 60) -> str | None:
        """Advance until a new contract is posted (or ``max_days`` pass). Returns its id."""
        for _ in range(max_days):
            if created := self.step():
                return created[0]
        return None

    # --- player actions -------------------------------------------------------------------------

    def accept(self, contract_id: str) -> str:
        return apply_action(self.world, "accept", contract_id=contract_id)

    def buy(self, good: str, qty: int) -> int:
        return apply_action(self.world, "buy", good=good, qty=qty)

    def caravan(self, good: str, qty: int) -> int:
        return apply_action(self.world, "caravan", good=good, qty=qty)

    def deliver(self, contract_id: str) -> str:
        return apply_action(self.world, "deliver", contract_id=contract_id)

    def abandon(self, contract_id: str) -> str:
        return apply_action(self.world, "abandon", contract_id=contract_id)

    def shock(
        self, effect: str, factor: float, duration: int, name: str, site: str | None = None
    ) -> str:
        return apply_action(
            self.world,
            "shock",
            effect=effect,
            factor=factor,
            duration=duration,
            name=name,
            site=site,
        )

    # --- contracts ------------------------------------------------------------------------------

    def contracts(self, status: str | None = None) -> list[Contract]:
        cs = sorted(self.world.contracts.contracts.values(), key=lambda c: c.id)
        return [c for c in cs if status is None or c.status is Status(status)]

    def contract(self, contract_id: str) -> Contract:
        try:
            return self.world.contracts.contracts[contract_id]
        except KeyError:
            raise UnknownIdError(f"unknown contract {contract_id!r}") from None

    def summarise(self, contract_id: str) -> str:
        """The quest in one short paragraph: root cause, key effect, who pays for what."""
        return summarise(self.world, self.contract(contract_id))

    def explain(self, contract_id: str) -> list[str]:
        """ "Why does this quest exist?" as sentences, root cause first."""
        names = {n.id: n.name for n in self.world.npcs.values()}
        return self.contract(contract_id).provenance.render(names)

    def quote(self, contract_id: str) -> Quote | None:
        """Estimated profit if you sourced this contract the cheapest feasible way today."""
        return quote_contract(self.world, self.contract(contract_id))

    def verify(self, contract_id: str) -> list[str]:
        """Re-measure every recorded number in the contract's provenance; [] means it holds."""
        return verify(self.world, self.contract(contract_id))

    def evidence_series(self, contract_id: str, step: int) -> dict[int, float]:
        """Day-by-day values of one measured step in a contract's chain, for charting it."""
        ev = self.contract(contract_id).provenance.chain[step]
        if ev.measure is None:
            raise ValueError(f"step {step} of {contract_id} ({ev.kind}) is not a measured value")
        return series(self.world, ev.measure[0])

    def graph(self, contract_id: str) -> dict[str, Any]:
        """The causal chain as JSON-ready nodes (evidence) and edges (cause to effect)."""
        return causes.graph(self.world, self.contract(contract_id))

    def lineage(self, contract_id: str) -> dict[str, list[str]]:
        board = self.world.contracts
        return {"ancestors": board.ancestors(contract_id), "children": board.children(contract_id)}

    # --- inspection -----------------------------------------------------------------------------

    def player(self) -> dict[str, Any]:
        ledger = self.world.ledger
        return {
            "coin": ledger.balance(PLAYER, Asset.COIN),
            "goods": {str(g): q for g in GOODS if (q := ledger.balance(PLAYER, g))},
            "reputation": {g.id: g.reputation.get(PLAYER, 0) for g in self.world.guilds.values()},
            "caravans": [
                {"arrives": t, "good": g, "qty": q} for t, g, q in self.world.pending_caravans
            ],
            "accepted": [c.id for c in self.contracts("accepted")],
        }

    def prices(self) -> dict[str, float]:
        return {str(g): round(p, 2) for g, p in self.world.prices.items()}

    def npc(self, npc_id: str) -> dict[str, Any]:
        try:
            n = self.world.npcs[npc_id]
        except KeyError:
            raise UnknownIdError(f"unknown npc {npc_id!r}") from None

        ledger = self.world.ledger
        return {
            "id": n.id,
            "name": n.name,
            "profession": str(n.profession),
            "guild": n.guild_id,
            "state": str(n.state),
            "coin": ledger.balance(n.account, Asset.COIN),
            "goods": {str(g): q for g in GOODS if (q := ledger.balance(n.account, g))},
            "at_site": {str(g): q for g in GOODS if (q := ledger.balance(n.site_account, g))}
            if n.site_account != n.account
            else {},
            "equipment_condition": round(n.tool_condition, 2),
            "hunger": n.hunger,
            "traits": dataclasses.asdict(n.traits),
            "needs": {str(g): d for g, d in n.unmet_streak.items()},
        }

    def guild(self, guild_id: str) -> dict[str, Any]:
        try:
            g = self.world.guilds[guild_id]
        except KeyError:
            raise UnknownIdError(f"unknown guild {guild_id!r}") from None

        return {
            "id": g.id,
            "name": g.name,
            "members": len(g.members),
            "treasury": self.world.ledger.balance(g.account, Asset.COIN),
            "reserve": g.policy.reserve,
            "reputation": dict(g.reputation),
        }

    def timeseries(self) -> dict[str, Any]:
        """Per-day series (prices, production, unfilled demand, hunger, treasuries...)."""
        return timeseries(self.world)

    def summary(self) -> dict[str, Any]:
        """Headline indicators for the run so far."""
        cs = self.contracts()
        suppressed: Counter[str] = Counter()
        for s in self.world.stats:
            if s.contracts:
                suppressed.update(s.contracts.suppressed)
        return {
            "day": self.day,
            "contracts": dict(Counter(str(c.status) for c in cs)),
            "contracts_by_kind": dict(Counter(str(c.kind) for c in cs)),
            "suppressed": dict(suppressed),
            "hungry_npcs": self.world.stats[-1].hungry_npcs if self.world.stats else 0,
            "prices": self.prices(),
            "state_hash": self.world.state_hash(),
        }
