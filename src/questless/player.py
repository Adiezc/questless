# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Player actions. Every action goes through ``apply_action``, which validates it, applies it
through the ledger, and appends it to the world's action log. Replaying the scenario with the same
log reproduces the world exactly.

The player has no goods of their own: to deliver, they must *source* them.
- ``buy``: from NPC sellers at today's market price. Real trades, so buying up scarce goods leaves
  less for everyone else and pushes the price up.
- ``caravan``: import goods from outside the map (the next town) at a markup; arrives after
  ``caravan_days``. Imports come out of the finite ``outside`` stock and the coin goes there, so
  nothing is created.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from questless.config import ShockEffect
from questless.contracts.engine import adjust_reputation
from questless.contracts.model import Contract, ContractKind, Status
from questless.sim.alloc import allocate
from questless.sim.entities import IN_TRANSIT, OUTSIDE, PLAYER, TOWN, Site
from questless.sim.ledger import GOODS, Asset
from questless.sim.market import stock_target
from questless.sim.shocks import Shock

if TYPE_CHECKING:
    from questless.sim.world import World


class ActionError(ValueError):
    """The action is not allowed in the current state. Nothing was changed."""


def apply_action(world: World, action: str, **args: Any) -> Any:
    handler = ACTIONS.get(action)
    if handler is None:
        raise ActionError(f"unknown action {action!r}; known: {', '.join(sorted(ACTIONS))}")
    result = handler(world, **args)
    world.actions.append({"tick": world.tick, "action": action, "args": args})
    return result


def accept(world: World, contract_id: str) -> str:
    c = _contract(world, contract_id)
    if c.status is not Status.OPEN:
        raise ActionError(f"{contract_id} is {c.status}, not open")
    world.contracts.accept(world, contract_id, PLAYER)
    return contract_id


def buy(world: World, good: str, qty: int) -> int:
    """Buy up to ``qty`` from NPCs holding more than they need. Returns units bought."""
    asset = _good(good)
    qty = _positive(qty)
    price = world.unit_price(asset)
    affordable = world.ledger.balance(PLAYER, Asset.COIN) // price
    asks = _asks(world, asset)
    want = min(qty, affordable)
    if not asks or want <= 0:
        raise ActionError(f"nobody is selling {good} (or you cannot afford it at {price})")
    sold = allocate(want, asks, world.rng.stream("player"))
    tax_rate = world.config.town.market_tax
    for seller, units in sorted(sold.items()):
        if not units:
            continue
        value = units * price
        world.ledger.transfer(
            seller, PLAYER, asset, units, tick=world.tick, reason="sale to player"
        )
        world.ledger.transfer(
            PLAYER, seller, Asset.COIN, value, tick=world.tick, reason="player pays"
        )
        world.ledger.transfer(
            seller, TOWN, Asset.COIN, int(value * tax_rate), tick=world.tick, reason="market tax"
        )
    return sum(sold.values())


def caravan(world: World, good: str, qty: int) -> int:
    """Order goods from outside. Returns the arrival tick."""
    asset = _good(good)
    qty = _positive(qty)
    if world.ledger.balance(OUTSIDE, asset) < qty:
        raise ActionError(f"no caravan carries {good} (outside stock too low)")
    cost = _caravan_cost(world, asset, qty)
    if world.ledger.balance(PLAYER, Asset.COIN) < cost:
        raise ActionError(f"a caravan of {qty} {good} costs {cost} coin")
    world.ledger.transfer(PLAYER, OUTSIDE, Asset.COIN, cost, tick=world.tick, reason="caravan")
    # Reserve the goods now so two caravans cannot sell the same stock.
    world.ledger.transfer(OUTSIDE, IN_TRANSIT, asset, qty, tick=world.tick, reason="caravan")
    arrival = world.tick + world.config.contracts.caravan_days
    world.pending_caravans.append((arrival, str(asset), qty))
    return arrival


def deliver(world: World, contract_id: str) -> str:
    c = _contract(world, contract_id)
    if c.status is not Status.ACCEPTED:
        raise ActionError(f"accept {contract_id} before delivering it")
    if c.kind.value != "transport" and world.ledger.balance(PLAYER, c.good) < c.qty:
        have = world.ledger.balance(PLAYER, c.good)
        raise ActionError(f"{contract_id} needs {c.qty} {c.good}; you have {have}")
    try:
        world.contracts.fulfil(world, contract_id, PLAYER)
    except ValueError as exc:
        raise ActionError(str(exc)) from exc
    hauled = c.outcome.get("hauled", c.qty)
    rep_earned = (c.rep_reward * hauled) // c.qty if c.qty > 0 else c.rep_reward
    adjust_reputation(world, c, +rep_earned)
    return contract_id


def abandon(world: World, contract_id: str) -> str:
    """Give an accepted contract back. It reopens for the rest of its time; reputation suffers."""
    c = _contract(world, contract_id)
    if c.status is not Status.ACCEPTED:
        raise ActionError(f"{contract_id} is not accepted")
    adjust_reputation(world, c, -c.rep_reward)  # needs accepted_by, so before clearing it
    c.status = Status.OPEN
    c.accepted_by = None
    return contract_id


def shock(
    world: World, effect: str, factor: float, duration: int, name: str, site: str | None = None
) -> str:
    """Introduce an economic shock starting today."""
    try:
        eff = ShockEffect(effect)
        where = Site(site) if site else None
    except ValueError as exc:
        raise ActionError(str(exc)) from None
    if eff is ShockEffect.SITE_OUTPUT and where is None:
        raise ActionError("site_output shocks need a site")
    _positive(duration)
    if not math.isfinite(factor):
        raise ActionError("factor must be a finite number")
    if factor < 0:
        raise ActionError("factor must be >= 0")
    world.modifiers.add(Shock(name, eff, world.tick, world.tick + duration, factor, where, "user"))
    return name


ACTIONS: dict[str, Callable[..., Any]] = {
    "accept": accept,
    "buy": buy,
    "caravan": caravan,
    "deliver": deliver,
    "abandon": abandon,
    "shock": shock,
}


@dataclass(frozen=True, slots=True)
class Quote:
    """What a contract would earn the player if sourced the cheapest feasible way today."""

    source: str  # "market", "caravan", "in hand" (already holding enough) or "haul" (transport)
    cost: int
    profit: int  # reward - cost; can be negative


def quote_buy(world: World, asset: Asset, qty: int) -> int | None:
    """Coin to buy ``qty`` at today's price, or ``None`` if sellers hold fewer than that.
    Pure: reads the same surplus ``buy`` would, changes nothing."""
    if sum(units for _, units in _asks(world, asset)) < qty:
        return None
    return qty * world.unit_price(asset)


def quote_caravan(world: World, asset: Asset, qty: int) -> int | None:
    """Coin for a caravan of ``qty``, or ``None`` if the outside stock is too low. Pure."""
    if world.ledger.balance(OUTSIDE, asset) < qty:
        return None
    return _caravan_cost(world, asset, qty)


def quote_contract(world: World, contract: Contract) -> Quote | None:
    """Estimated profit for ``contract``: reward minus the cheaper of buying the missing units at
    market or importing them by caravan in time. ``None`` if neither can source them. Only an
    estimate: buying moves the price, and other buyers may get there first."""
    if contract.kind is ContractKind.TRANSPORT:  # the player hauls what is already there
        current_backlog = sum(
            min(qty, world.ledger.balance(world.npcs[nid].site_account, contract.good))
            for nid, qty in contract.beneficiaries.items()
            if nid in world.npcs
        )
        if current_backlog <= 0:
            return None
        est_reward = (contract.reward * current_backlog) // contract.qty
        return Quote("haul", 0, est_reward)
    missing = max(contract.qty - world.ledger.balance(PLAYER, contract.good), 0)
    if not missing:
        return Quote("in hand", 0, contract.reward)
    options = [("market", quote_buy(world, contract.good, missing))]
    if world.tick + world.config.contracts.caravan_days < contract.deadline_tick:
        options.append(("caravan", quote_caravan(world, contract.good, missing)))
    feasible = [(cost, source) for source, cost in options if cost is not None]
    if not feasible:
        return None
    cost, source = min(feasible)
    return Quote(source, cost, contract.reward - cost)


def receive_caravans(world: World) -> None:
    """Called at the start of each tick: caravans due today unload into the player's stock."""
    due = [c for c in world.pending_caravans if c[0] <= world.tick]
    world.pending_caravans = [c for c in world.pending_caravans if c[0] > world.tick]
    for _, good, qty in sorted(due):
        world.ledger.transfer(
            IN_TRANSIT, PLAYER, Asset(good), qty, tick=world.tick, reason="caravan"
        )


def _contract(world: World, contract_id: str):
    c = world.contracts.contracts.get(contract_id)
    if c is None:
        raise ActionError(f"no contract {contract_id}")
    if world.tick >= c.deadline_tick:
        raise ActionError(f"{contract_id} has passed its deadline")
    return c


def _asks(world: World, asset: Asset) -> list[tuple[str, int]]:
    """NPCs holding more ``asset`` than they want, with how many they would sell."""
    asks = []
    for npc in world.npcs_in_order():
        surplus = world.ledger.balance(npc.account, asset) - stock_target(world, npc, asset)
        if surplus > 0:
            asks.append((npc.id, surplus))
    return asks


def _caravan_cost(world: World, asset: Asset, qty: int) -> int:
    return math.ceil(qty * world.config.goods[asset].base_price * world.config.caravan_markup)


def _good(name: str) -> Asset:
    try:
        asset = Asset(name)
    except ValueError:
        raise ActionError(f"unknown good {name!r}") from None
    if asset not in GOODS:
        raise ActionError("coin is not a good")
    return asset


def _positive(qty: int) -> int:
    if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
        raise ActionError(f"quantity must be a positive integer, got {qty!r}")
    return qty
