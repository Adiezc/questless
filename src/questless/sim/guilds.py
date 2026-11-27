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
- **Loans** (off unless ``loan_limit`` > 0): after relief, a member that can't afford to work (a
  crafter short of inputs, anyone short of a replacement for broken equipment) borrows enough to
  bid for them (``loan_target``), while its debt stays within
  ``loan_limit`` coin and the treasury above half its reserve. It repays ``loan_repay_share`` of
  each day's gain before dues. Relief alone is a gift capped above the reserve, so a guild
  whose treasury sits at its reserve can't get a broke smith or miner back to work; a loan comes
  back (VALIDATION.md D3).

With guilds disabled no guild accounts exist and none of this runs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from questless.sim.ledger import Asset

if TYPE_CHECKING:
    from questless.sim.world import World

DUES_CARRY = "guild_dues"
LOAN = "guild_loan"  # a member's outstanding debt to its guild, in ``NPC.carry``


@dataclass(frozen=True, slots=True)
class GuildReport:
    guild_id: str
    dues: int
    relief: int
    relief_recipients: int
    treasury: int  # end of day, after today's contracts took or returned escrow
    escrowed: int = 0  # coin this guild has locked in live contracts, end of day
    upkeep: int = 0  # town levy paid today on coin above ``policy.max_treasury``
    loans: int = 0  # coin lent to members today
    repaid: int = 0  # coin members repaid today


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


def lend_working_capital(world: World) -> dict[str, dict[str, int]]:
    """Lend members who can't afford to work: a crafter short of inputs, or anyone short of a
    replacement for broken equipment. Returns ``{guild_id: {npc_id: amount}}``.

    The loan tops the wallet up to ``loan_target``: enough that, after the food reserve
    ``market.budget`` holds back, the crafter can actually bid for inputs and equipment. A loan
    sized to relief's working capital goes on food instead. Loans stop at the member's
    ``loan_limit`` and never take the treasury below half its reserve."""
    lent: dict[str, dict[str, int]] = {}
    for gid, guild in sorted(world.guilds.items()):
        lent[gid] = {}
        policy = guild.policy
        if policy.loan_limit <= 0:
            continue
        for member in sorted(guild.members):
            npc = world.npcs[member]
            if not working_capital(world, member, 0):  # no broken kit to replace, no inputs
                continue
            short = loan_target(world, member) - world.ledger.balance(member, Asset.COIN)
            debt = int(npc.carry.get(LOAN, 0))
            spare = world.ledger.balance(guild.account, Asset.COIN) - policy.reserve // 2
            if short <= 0 or short > spare or debt + short > policy.loan_limit:
                continue
            world.ledger.transfer(
                guild.account, member, Asset.COIN, short, tick=world.tick, reason="guild loan"
            )
            npc.carry[LOAN] = float(debt + short)
            lent[gid][member] = short
    return lent


def loan_target(world: World, npc_id: str) -> int:
    """Wallet a member needs so that ``market.budget`` lets it buy a replacement for broken
    equipment and (for a crafter) one craft's inputs, with its food reserve kept and today's food
    still to buy. Zero for a member with nothing to buy."""
    from questless.sim.market import stock_target

    npc = world.npcs[npc_id]
    kit = working_capital(world, npc_id, 0)  # equipment if broken, plus one craft's inputs
    reserve = stock_target(world, npc, Asset.FOOD) * world.unit_price(Asset.FOOD)
    spendable = max(math.ceil(kit / (1 - npc.traits.thrift)), kit + reserve) if kit else 0
    return spendable + reserve


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
    """Charge each member ``dues_rate`` of today's net coin gain, excluding relief (and loans)
    received. Loan repayments run first, so what a member repays isn't charged dues."""
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


def collect_repayments(
    world: World, start_coin: dict[str, int], received: dict[str, dict[str, int]]
) -> dict[str, int]:
    """Each indebted member repays ``loan_repay_share`` of today's gain (excluding relief and
    loans received), at most its debt and its wallet. Returns ``{npc_id: amount}``."""
    got = {npc: amt for per_guild in received.values() for npc, amt in per_guild.items()}
    repaid: dict[str, int] = {}
    for _, guild in sorted(world.guilds.items()):
        for member in guild.members:
            npc = world.npcs[member]
            debt = int(npc.carry.get(LOAN, 0))
            if debt <= 0:
                continue
            wallet = world.ledger.balance(member, Asset.COIN)
            gain = wallet - start_coin[member] - got.get(member, 0)
            pay = min(debt, int(max(gain, 0) * guild.policy.loan_repay_share), wallet)
            if pay <= 0:
                continue
            world.ledger.transfer(
                member, guild.account, Asset.COIN, pay, tick=world.tick, reason="loan repayment"
            )
            npc.carry[LOAN] = float(debt - pay)
            repaid[member] = pay
    return repaid


def reports(
    world: World,
    dues: dict[str, int],
    relief: dict[str, dict[str, int]],
    upkeep: dict[str, int] | None = None,
    loans: dict[str, dict[str, int]] | None = None,
    repaid: dict[str, int] | None = None,
) -> dict[str, GuildReport]:
    return {
        gid: GuildReport(
            guild_id=gid,
            dues=dues.get(gid, 0),
            relief=sum(relief.get(gid, {}).values()),
            relief_recipients=len(relief.get(gid, {})),
            treasury=world.ledger.balance(guild.account, Asset.COIN),
            upkeep=(upkeep or {}).get(gid, 0),
            loans=sum((loans or {}).get(gid, {}).values()),
            repaid=sum(v for m, v in (repaid or {}).items() if m in guild.members),
        )
        for gid, guild in sorted(world.guilds.items())
    }


def close_reports(world: World, reports: dict[str, GuildReport]) -> dict[str, GuildReport]:
    """Re-read treasuries once the contract board has run, so a report matches the live balance.

    Posting a contract moves its reward from the funder into escrow, and expiry refunds it; both
    happen after dues. ``escrowed`` is the coin each guild still has locked in live contracts.
    """
    locked: dict[str, int] = {}
    for c in world.contracts.live():
        locked[c.funder] = locked.get(c.funder, 0) + c.reward
    return {
        gid: replace(
            report,
            treasury=world.ledger.balance(world.guilds[gid].account, Asset.COIN),
            escrowed=locked.get(world.guilds[gid].account, 0),
        )
        for gid, report in reports.items()
    }
