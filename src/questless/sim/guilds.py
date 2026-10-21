# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Guild economics: dues in, relief out. Contract funding is added in milestone M5.

- **Dues:** each member pays ``dues_rate`` of their net coin gain for the day (relief excluded),
  with fractions carried over so small incomes are not rounded away.
- **Relief:** members who cannot afford ``relief_days`` of food are topped up from the treasury,
  poorest first, until the day's relief budget (``max_daily_relief_share`` of the treasury) runs
  out, and never below the guild's ``reserve``. This is a safety net, not a wage: it only ever
  covers food money.

With guilds disabled no guild accounts exist and none of this runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from questless.sim.ledger import Asset

if TYPE_CHECKING:
    from questless.sim.world import World

DUES_CARRY = "guild_dues"


@dataclass(frozen=True, slots=True)
class GuildReport:
    guild_id: str
    dues: int
    relief: int
    relief_recipients: int
    treasury: int  # end of day


def provide_relief(world: World) -> dict[str, dict[str, int]]:
    """Top up broke members. Returns ``{guild_id: {npc_id: amount}}``."""
    food_per_day = world.config.needs.food_per_day
    food_price = world.unit_price(Asset.FOOD)
    paid: dict[str, dict[str, int]] = {}
    for gid, guild in sorted(world.guilds.items()):
        paid[gid] = {}
        days = guild.policy.relief_days
        if not days:
            continue
        floor = days * food_per_day * food_price
        treasury = world.ledger.balance(guild.account, Asset.COIN)
        budget = min(
            int(treasury * guild.policy.max_daily_relief_share),
            max(treasury - guild.policy.reserve, 0),
        )
        wallets = {m: world.ledger.balance(m, Asset.COIN) for m in guild.members}
        for member in sorted(guild.members, key=lambda m: (wallets[m], m)):  # poorest first
            top_up = min(floor - wallets[member], budget)
            if top_up <= 0:
                continue
            world.ledger.transfer(
                guild.account, member, Asset.COIN, top_up, tick=world.tick, reason="guild relief"
            )
            paid[gid][member] = top_up
            budget -= top_up
    return paid


def collect_dues(
    world: World, start_coin: dict[str, int], relief: dict[str, dict[str, int]]
) -> dict[str, int]:
    """Charge each member ``dues_rate`` of today's net coin gain, excluding relief received."""
    received = {npc: amt for per_guild in relief.values() for npc, amt in per_guild.items()}
    collected: dict[str, int] = {}
    for gid, guild in sorted(world.guilds.items()):
        total = 0
        for member in guild.members:
            gain = world.ledger.balance(member, Asset.COIN) - start_coin[member]
            owed = max(gain - received.get(member, 0), 0) * guild.dues_rate
            # Carry fractions so small daily incomes still pay their share over time.
            npc = world.npcs[member]
            owed += npc.carry.get(DUES_CARRY, 0.0)
            dues = int(owed)
            npc.carry[DUES_CARRY] = round(owed - dues, 9)
            world.ledger.transfer(
                member, guild.account, Asset.COIN, dues, tick=world.tick, reason="guild dues"
            )
            total += dues
        collected[gid] = total
    return collected


def reports(
    world: World, dues: dict[str, int], relief: dict[str, dict[str, int]]
) -> dict[str, GuildReport]:
    return {
        gid: GuildReport(
            guild_id=gid,
            dues=dues.get(gid, 0),
            relief=sum(relief.get(gid, {}).values()),
            relief_recipients=len(relief.get(gid, {})),
            treasury=world.ledger.balance(guild.account, Asset.COIN),
        )
        for gid, guild in sorted(world.guilds.items())
    }
