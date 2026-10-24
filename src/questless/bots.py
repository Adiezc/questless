# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Scripted players that use only the public ``Simulation`` API, for experiments and exports."""

from __future__ import annotations

from typing import TYPE_CHECKING

from questless.contracts.model import ContractKind
from questless.player import ActionError
from questless.sim.ledger import Asset

if TYPE_CHECKING:
    from questless.api import Simulation

RAW = (Asset.FOOD, Asset.IRON_ORE)  # goods the settlement gathers rather than crafts
STRATEGIES = ("local", "importer")


class ScriptedPlayer:
    """A simple, greedy, honest player: holds at most ``max_live`` contracts, prefers the best
    reward, and delivers as soon as the goods are in hand. It uses only the public API, so it
    obeys every rule a human player does. Two sourcing strategies:

    - ``importer``: caravan first (any good the next town sells), the market as fallback.
    - ``local``: the market first; caravans only for raw goods (food, ore), never for crafted
      goods that local smiths make. It only takes contracts it can source this way.
    """

    def __init__(self, sim: Simulation, strategy: str, max_live: int = 3) -> None:
        self.sim = sim
        self.strategy = strategy
        self.max_live = max_live
        self.sourced: set[str] = set()

    def act(self) -> None:
        sim = self.sim
        for c in sim.contracts("accepted"):
            needs_goods = c.kind is not ContractKind.TRANSPORT
            held = sim.player()["goods"].get(str(c.good), 0)
            if not needs_goods or held >= c.qty:
                self._try(sim.deliver, c.id)
            elif c.id not in self.sourced and self._source(str(c.good), c.qty - held, c.good):
                self.sourced.add(c.id)
        live = len(sim.contracts("accepted"))
        for c in sorted(sim.contracts("open"), key=lambda c: -c.reward):
            if live >= self.max_live:
                break
            if self._worth_taking(c) and self._try(sim.accept, c.id):
                live += 1

    def _source(self, good: str, qty: int, asset: Asset) -> bool:
        sim = self.sim
        if self.strategy == "importer":
            return self._try(sim.caravan, good, qty) or self._try(sim.buy, good, qty)
        if self._try(sim.buy, good, qty):  # partial buys are fine; the rest next day
            return sim.player()["goods"].get(good, 0) >= qty
        return asset in RAW and self._try(sim.caravan, good, qty)

    def _worth_taking(self, c) -> bool:
        sim = self.sim
        cost = c.qty * sim.config.goods[c.good].base_price * sim.config.caravan_markup
        affordable = sim.player()["coin"] >= cost
        in_time = c.deadline_tick - sim.day > sim.config.contracts.caravan_days
        # The local strategy never takes crafted goods: it would have to import them.
        local_ok = self.strategy != "local" or c.kind is ContractKind.TRANSPORT or c.good in RAW
        return affordable and in_time and local_ok

    @staticmethod
    def _try(fn, *args) -> bool:
        try:
            fn(*args)
            return True
        except ActionError:
            return False
