# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Exploit hunters (M52.0): scripted players that try to earn more than an honest one.

Each attacker sees only what a player sees, through ``Simulation``: the public board, prices, its
own wallet and the scenario (including its shock schedule, which the scenario file publishes).
Every move goes through the player actions, so each run is a replayable save.

- ``Squatter`` (claim and wait): accepts many contracts at once, buys only when the good is at or
  below its base price, and delivers just before the deadline. Accepted contracts are never
  cancelled when the need goes away, so the reward is still paid after prices fall.
- ``Hoarder`` (buy before a scheduled shock): the day before a shock hits a site, spends half its
  coin on that site's goods, then fulfils the contracts the shortage creates from its own stock.
- ``Flipper`` (accept and abandon): accepts every open contract it can afford, keeps the ones it
  can source at or below base price that day and abandons the rest, so it never holds a losing
  contract for long.
- ``Prober`` (deliver before sourcing): accepts every open contract and tries to deliver it at
  once, holding nothing, then abandons what the rules refuse. Honest play never tries this, so it
  is what finds a rule that pays for nothing (like #43, where a transport contract paid in full
  for hauling nothing).
"""

from __future__ import annotations

from questless.config import ShockEffect
from questless.contracts.model import ContractKind
from questless.player import ActionError

SITE_GOODS = {"mine": ("iron_ore",), "farms": ("food",)}


def _try(fn, *args) -> bool:
    try:
        fn(*args)
        return True
    except ActionError:
        return False


def _cheap(sim, good: str) -> bool:
    return sim.prices()[good] <= sim.config.goods[_asset(sim, good)].base_price


def _asset(sim, good: str):
    return next(g for g in sim.config.goods if str(g) == good)


def _held(sim, good: str) -> int:
    return sim.player()["goods"].get(good, 0)


def _deliver_ready(sim) -> None:
    for c in sim.contracts("accepted"):
        if c.kind is ContractKind.TRANSPORT or _held(sim, str(c.good)) >= c.qty:
            _try(sim.deliver, c.id)


class Squatter:
    """Claim and wait: up to ``max_live`` contracts, sourced only when cheap or nearly due."""

    def __init__(self, sim, max_live: int = 10) -> None:
        self.sim, self.max_live = sim, max_live

    def act(self) -> None:
        sim = self.sim
        for c in sim.contracts("accepted"):
            good = str(c.good)
            due = c.deadline_tick - sim.day <= sim.config.contracts.caravan_days + 1
            missing = c.qty - _held(sim, good)
            if c.kind is ContractKind.TRANSPORT or missing <= 0:
                if due or c.kind is ContractKind.TRANSPORT:
                    _try(sim.deliver, c.id)
            elif _cheap(sim, good) or due:
                _try(sim.buy, good, missing)
                if due and _held(sim, good) < c.qty:
                    _try(sim.caravan, good, c.qty - _held(sim, good))
        live = len(sim.contracts("accepted"))
        for c in sorted(sim.contracts("open"), key=lambda c: -c.reward):
            if live >= self.max_live:
                break
            if c.deadline_tick - sim.day > sim.config.contracts.caravan_days and _try(
                sim.accept, c.id
            ):
                live += 1


class Hoarder:
    """Buy before a scheduled shock, then sell into the shortage through contracts."""

    def __init__(self, sim, honest_cls, share: float = 0.5) -> None:
        self.sim, self.share = sim, share
        self.honest = honest_cls(sim, "local")

    def act(self) -> None:
        sim = self.sim
        for shock in sim.config.shocks:
            if shock.effect is ShockEffect.SITE_OUTPUT and shock.start - 1 == sim.day:
                for good in SITE_GOODS.get(str(shock.site), ()):
                    price = max(1, round(sim.prices()[good]))
                    _try(sim.buy, good, int(sim.player()["coin"] * self.share) // price)
        _deliver_ready(sim)
        self.honest.act()


class Flipper:
    """Accept everything affordable; keep what is cheap to source today, abandon the rest."""

    def __init__(self, sim) -> None:
        self.sim = sim

    def act(self) -> None:
        sim = self.sim
        _deliver_ready(sim)
        for c in sorted(sim.contracts("open"), key=lambda c: -c.reward):
            _try(sim.accept, c.id)
        for c in sim.contracts("accepted"):
            good = str(c.good)
            if c.kind is ContractKind.TRANSPORT:
                continue
            missing = c.qty - _held(sim, good)
            if missing > 0 and not (_cheap(sim, good) and _try(sim.buy, good, missing)):
                _try(sim.abandon, c.id)
        _deliver_ready(sim)


class Prober:
    """Accept everything and try to deliver it before sourcing anything; abandon the refusals."""

    def __init__(self, sim) -> None:
        self.sim = sim

    def act(self) -> None:
        sim = self.sim
        for c in sorted(sim.contracts("open"), key=lambda c: -c.reward):
            _try(sim.accept, c.id)
        for c in sim.contracts("accepted"):
            if not _try(sim.deliver, c.id):
                _try(sim.abandon, c.id)
