# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Guild economics: dues in, relief out. Contract funding is added in milestone M5.

- **Dues:** each member pays ``dues_rate`` of their net coin gain for the day (relief excluded),
  with fractions carried over so small incomes are not rounded away.
- **Relief:** members who cannot afford to keep working are topped up from the treasury, poorest
  first, until the day's relief budget (``max_daily_relief_share`` of the treasury) runs out, and
  never below the guild's ``reserve``. "Able to work" means ``relief_days`` of food, a replacement
  for broken equipment, and inputs for one craft (see ``working_capital``). It is working
  capital, not a wage: a member who is not short of these gets nothing.

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
    """Top up broke members to ``working_capital``. Returns ``{guild_id: {npc_id: amount}}``."""
    paid: dict[str, dict[str, int]] = {}
    for gid, guild in sorted(world.guilds.items()):
        paid[gid] = {}
        days = guild.policy.relief_days
        if not days:
            continue
        treasury = world.ledger.balance(guild.account, Asset.COIN)
        budget = min(
            int(treasury * guild.policy.max_daily_relief_share),
            max(treasury - guild.policy.reserve, 0),
        )
        wallets = {m: world.ledger.balance(m, Asset.COIN) for m in guild.members}
        for member in sorted(guild.members, key=lambda m: (wallets[m], m)):  # poorest first
            top_up = min(working_capital(world, member, days) - wallets[member], budget)
            if top_up <= 0:
                continue
            world.ledger.transfer(
                guild.account, member, Asset.COIN, top_up, tick=world.tick, reason="guild relief"
            )
            paid[gid][member] = top_up
            budget -= top_up
    return paid


def working_capital(world: World, npc_id: str, food_days: int) -> int:
    """Coin a member needs to keep working: ``food_days`` of food, a replacement for broken
    equipment it has no spare of, and inputs for one craft."""
    npc = world.npcs[npc_id]
    pc = world.config.professions[npc.profession]
    need = food_days * world.config.needs.food_per_day * world.unit_price(Asset.FOOD)
    broken = npc.tool_condition < world.config.needs.equipment_threshold
    if pc.equipment is not None and broken and not world.ledger.balance(npc_id, pc.equipment):
        need += world.unit_price(pc.equipment)
    if pc.recipes:
        need += min(
            sum(world.unit_price(a) * q for a, q in inputs.items())
            for inputs in pc.recipes.values()
        )
    return need


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
