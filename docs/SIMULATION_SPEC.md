# Simulation specification (as implemented, v0.1.0)

All numbers are the baseline values in [`scenarios/baseline.toml`](../scenarios/baseline.toml),
where each one is commented. This document describes the rules. [PLAN.md](PLAN.md) section C is
the original design; the differences are listed at the end.

## Goods, accounts, conservation

- **Goods:** `food`, `iron_ore`, `tools`, `weapons`, plus `coin`.
- **Accounts:** one per NPC; `npc@mine` / `npc@farms` for output awaiting transport; one per
  guild; `town`; `escrow`; `player`; `market` (clearing account, always empty between trades);
  `outside` (the next town); `in_transit` (paid-for caravan goods).
- **Operations:** `transfer`, `produce` (goods only), `consume` (goods only), and genesis.
- **Invariant, checked every tick:** for every asset, `sum(balances) == genesis + produced -
  consumed`. Coin supply is fixed. No balance is ever negative.

## NPCs and production

| Profession | Count | Site | Daily rule (× skill × modifiers) | Equipment wear |
|---|---|---|---|---|
| Farmer | 34 | farms | +3.3 food × effort | tools 0.10 |
| Miner | 16 | mine | +1.4 iron ore × effort | tools 0.10 |
| Blacksmith | 8 | market | 2 crafts: tools = 2 ore, weapons = 3 ore | tools 0.10 |
| Merchant | 14 | market | 14 units/day transport capacity | none |
| Guard | 28 | market | paid 7 coin/day by the town | weapons 0.05 |

- **Traits (seeded per NPC):** skill 0.8-1.2, thrift 0.1-0.5, stock_days 2-5, patience 2-5.
- **Productivity:** skill × site shock factor, × 0.5 if hungry for more than 2 days, × the
  profession's no-tool factor if equipment is broken with no spare.
- **Effort:** gatherers' output scales with `price / base price`, clamped to [0.6, 1.3]. This is
  the supply curve.
- **Production cap:** a producer pauses once its unsold stock exceeds 6 days of its recent
  sales (7-day average, floored at half its base rate).
- **Crafting:** among recipes below their cap, smiths craft the one with the best margin per unit
  of input that their stock allows.

## Market (once per good per day)

- **Asks:** each NPC offers its holdings above its stock target. The target is food for
  `stock_days`, plus one spare piece of equipment, plus craft inputs for `stock_days`.
- **Bids:** each NPC bids for what it lacks below its target, within its budget. Food may use
  the whole wallet. Anything else must leave max(thrift × wallet, the cost of its food target).
  Crafters only buy inputs while some recipe is profitable.
- **Fills:**
  - The short side is filled in full.
  - Excess supply is split across sellers pro rata.
  - Excess demand is **rationed equally** across buyers.
  - Trades settle at the integer price; sellers pay 5% tax to the town.
- **Price update:**
  `p' = clamp(p × (1 + 0.05 × signal), 0.25×base, 4×base)`, where
  `signal = clamp((consumed - produced)/max(...) + 0.5 × (3 - supply/demand)/3, -1, 1)`.
- **Exports:** outside traders spend 20% of their coin per day on surplus.

## Money loop

- **Town:** levies 3% a day on NPC coin above 60 and on guild treasuries above their
  `max_treasury` (3,000 in the baseline), and pays guard wages.
- **Haulage:** 20% of shipped goods' value, pooled and split by merchant capacity.
- **Guild dues:** 5% of a member's net daily gain, with fractional carry.
- **Guild relief:** a broke member is topped up to *working capital*: 2 days of food, a
  replacement for broken equipment, and one craft's inputs. Poorest first, at most 5% of the
  treasury per day, never below a 500-coin reserve.

## Needs

- **Scarcity day:** the NPC could not do something it needed (`unmet > 0`) *and* bid at market,
  could pay, and got nothing (`unfilled > 0`).
- **Poverty:** unmet and could not pay. Counted separately; it never produces a contract.
- **Persistence:** a streak survives a 1-day gap and becomes persistent at the NPC's `patience`.
- **Transport need:** site backlog above 3 days of output while market buyers go unfilled.

## Contracts

| Kind | Requester | Fires when |
|---|---|---|
| Guild supply | a guild | ≥60% of members *who use the good* are short, and one has run out of patience |
| Town supply | the town | ≥40% of guards are short |
| Procurement | one NPC | a persistent need not covered by a live pooled contract |
| Transport | producers' guild or the town | a persistent transport need |

A candidate must pass these checks, in order, and every rejection is counted:

1. **Duplicate:** no other live contract for the same need.
2. **Cooldown:** the 5-day quiet period after a contract for the need closed.
3. **Caps:** at most 12 live contracts and 3 new ones per day.
4. **Feasible:** the goods can be obtained, from NPC surplus or outside stock.
5. **Funded:** the funder is tried in order: the NPC itself (its budget), then its guild (40% of
   treasury), then the town for guards (20% of treasury). Funding may be partial.
6. **Minimum reward:** 60 coin.

**Reward:** `qty × price × premium × urgency`, capped by what the funder can spend.
- Premium: 1.2 for NPCs, 1.3 for guilds, ±10% with reputation.
- Urgency: +10% per day the need persists beyond patience, up to 2×.

The reward is escrowed before the contract is posted.

**Lifecycle:**
- OPEN → ACCEPTED → FULFILLED (goods to beneficiaries, escrow to the player, reputation up).
- Unfulfilled contracts close as EXPIRED or CANCELLED. Either way the escrow is refunded and a
  cooldown starts. An open contract is withdrawn after its need has been calm for 3 days.
- Outcomes are recorded 7 days after delivery.

## Provenance

- **Order:** root causes come first in the chain, then contract-level facts (unfilled demand,
  need persisted, emergency share, partial funding, funding decision).
- **Causal walk** (`causes.py`), depth ≤ 3, each good visited once:
  - **Production drop:** last 3 days vs a 30-day baseline ending before the shock (or before the
    need began). Below 85% counts.
  - **Gathered goods:** site shocks and transport shocks are causes, plus rises of ≥15
    percentage points in producers' broken-equipment or hunger share. Each rise recurses into
    tools or food.
  - **Crafted goods:** a ≥15-point rise in crafters' idle share recurses into the inputs.
  - **Price spike:** ≥125% of the baseline price.
- **Lineage:** the most recent contract for an upstream good becomes the parent.
- **Verification:** measured evidence stores `(metric key, tick)`; `verify()` recomputes value
  and baseline from `TickStats` and checks the causal ordering.
- **Quest summary:** the middle step prefers evidence for the contract's good, in order of
  production drop, transport backlog, price spike and unfilled demand. If only an upstream
  good has such evidence, its own name labels the quoted numbers. Funding still names the
  contract's good and quantity.

## Player

- **Wallet:** starts with 600 coin.
- **buy:** from NPC surplus at today's price.
- **caravan:** from outside stock at 1.25 × base price; arrives after 3 days.
- **accept / deliver / abandon:** abandoning reopens the contract and costs reputation.
- **shock:** starts today.
- Every action is validated and logged. Invalid actions change nothing.

## Changes from the original plan (PLAN.md section C)

1. **Pricing:** stock-plus-flow signal and an effort supply curve, replacing the pure
   excess-demand rule (M3).
2. **Holdings:** live in the ledger, not on NPC fields (M1).
3. **Town supply** was added as a fourth contract kind (M5).
4. **Partial funding** (M5).
5. **Relief:** working capital instead of food money (M9).
6. **Imports:** caravans carry crafted goods too (M9).
7. **Rationing:** equal shares for buyers (M9).
8. **Pooling:** shares counted among users of the good (M9).
9. **Exports:** outside traders buy surplus (M11).
