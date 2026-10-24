# Validation: does the simulation behave like a real economy?

Researchers using Questless data (`questless export`) need to know which real-world patterns the
simulation reproduces, and where it doesn't. This page lists **stylized facts**: robust patterns
from the economics literature, each checked against the simulation on 5 seeds by
[`tests/test_stylized_facts.py`](../tests/test_stylized_facts.py), so the page can't silently go
stale.

**How to read it:** a fact that holds is a test that passes. A known divergence is a test marked
`xfail(strict=True)`: if someone fixes the model, the test fails until this page is updated. Every
number below comes from those tests' scenarios (120 days, seeds 1-5, except D2: 365 days, seeds 1-20) and was regenerated on
2026-10-24; scenario changes can move them.

**What a fact does and doesn't mean:** matching a pattern shows the model isn't wrong in that
respect, not that it is right. The simulation has 100 NPCs, four goods and no capital assets, so it
can only reproduce patterns that don't depend on what it leaves out (see
[Scope and limitations](../README.md#scope-and-limitations)).

## Summary

| # | Fact | Holds? | Simulation, 5 seeds |
|---|---|---|---|
| 1 | A supply shock raises the price of the good | Yes | Iron ore +15% to +35% during the mine disaster; food +56% to +57% during the drought |
| 2 | Prices return towards normal once supply recovers | Food yes, iron ore **no** (D1, a poverty trap) | Food ends 6% to 32% above normal; iron ore ends at 25% to 37% of normal on 4 seeds and near the price ceiling on 1 |
| 3 | A food shortage leaves people hungry | Yes | 0 hungry NPCs before the drought, 11 to 13 on average during it |
| 4 | Wealth ranks persist but are not fixed | Yes | Rank correlation of NPC coin between day 30 and day 120: 0.19 to 0.72 (mean 0.36 baseline, 0.51 Iron Shortage) |
| D2 | Wealth concentrates through returns on capital | **Right level, wrong cause** | Baseline coin Gini rises from 0.27 (day 120) to 0.49 (day 365, 20 seeds), with no capital to earn on |

## Facts

### 1. A supply shock raises the price of the good

**Evidence:** droughts raise local food prices, often before the harvest fails, as traders
anticipate the shortfall (Letta et al., 2021); grain prices rose about 40% during Iran's worst
drought (Kheyruri et al., 2023).

**Simulation:** the mean price during each shock is above the pre-shock mean (days 10-14) by more
than 10% on every seed. **Test:** `test_fact_1_a_supply_shock_raises_the_price`.

**Simpler than reality:** NPCs don't anticipate a shock (the schedule is hidden, #93), so prices
move only when supply falls, not before.

### 2. Prices return towards normal once supply recovers

**Evidence:** in Ethiopia, drought price rises come straight after the harvest and then dissipate
(Hill & Fuje, 2020). Over 150 years, mineral supply shocks move prices for up to five years, after
which prices return to trend (Stuermer, 2018).

**Simulation:** food prices in the last 20 days of a drought run are within 40% of normal on every
seed. Iron ore doesn't recover (divergence **D1**, below). **Tests:**
`test_fact_2_food_prices_come_back_after_a_drought` and the `xfail`
`test_fact_2_ore_prices_come_back_after_a_mine_disaster`.

### 3. A food shortage leaves people hungry

**Evidence:** a moderate drought cuts consumption by about 9% for many rural Ethiopian households,
which cannot protect themselves against it (Hill & Porter, 2017).

**Simulation:** on every seed, the average number of hungry NPCs during the drought is at least 5
above the number before it. **Test:** `test_fact_3_a_food_shortage_leaves_people_hungry`.

### 4. Wealth ranks persist but are not fixed

**Evidence:** in US tax records, a 10-percentile rise in parents' income goes with a 3.4-percentile
rise in their child's: a rank-rank slope of 0.34 (Chetty et al., 2014).

**Simulation:** the rank correlation of NPC coin between day 30 and day 120 averages 0.36 on the
baseline and 0.51 on Iron Shortage. **Test:** `test_fact_4_wealth_ranks_persist_but_are_not_fixed`
checks it stays between 0.1 and 0.8.

**Not the same measure:** Chetty et al. compare two generations; this compares one NPC 90 days
apart. The similar numbers are a coincidence of scale, not a calibration. Read it as "neither a
caste system nor a lottery", not as "US-like mobility".

## Known divergences

### D1. Iron ore prices don't recover after the mine disaster

After the mine reopens (day 55), the iron ore price settles at 2.3 to 3.5 coin on 4 of 5 seeds,
about a third of its pre-shock 8.5 to 9.4. On seed 5 it sticks at 30.8, near the ceiling of 32.
Real mineral prices return to trend after a supply shock (Stuermer, 2018).

**Cause: a poverty trap, not a supply problem.** During the shock miners sell almost nothing, wear
out their tools and run through their savings; smiths run out of ore and stop earning. By day 120
on seeds 2-4, the 16 miners hold 6 to 39 coin between them (about 1,700 to 2,050 on day 14), all
16 have no usable tool, and the 8 smiths hold 26 to 31. Coin has pooled with farmers, the only
sellers left (3,600 to 3,850 on day 14, 9,600 to 9,900 on day 120): that is the coin Gini of
0.66 to 0.67. From then on the market is frozen:

- Miners have 80 ore waiting to sell but no buyer, so they stop mining (their unsold-stock cap).
- Smiths would make a tool from 2 ore and sell it for 96, and buyers who can pay (all of them farmers)
  want 32 to 33 tools a day. But a smith may only spend coin above a food reserve of 2 to 5 days of food
  (`market.budget`), and with about 4 coin each and food near 15, that budget is 0.
- Guild relief can't help: every guild treasury is at its untouchable reserve of 500.

With ore on offer and no one able to bid, the price's stock term pushes it down 2.5% a day to the
floor of 2. So the low price measures the buyers' poverty, not plentiful ore. Nothing changes it:
on seed 3 the market is the same on day 300. Seed 1 is half-trapped (smiths recovered, miners didn't: 3 ore a day).
Seed 5 avoided the trap: by day 120 miners have re-tooled and mine 16 ore a day, and the ore price
is high because smiths are rebuilding the tool stock; it is falling again by day 145.

The scenario intends a slump the town can't leave alone ("player action matters", see
`scenarios/mine_disaster.toml` and REVIEW B3), so the trap stays: it is the designed behaviour, not
a bug to fix in the NPC economy. **But a player can't get the town out of it yet either.** With
the scripted player from `questless.bots` in the run, iron ore ends at 0.38 to 1.02 times its
pre-shock price with the `local` strategy (recovered on 1 of 5 seeds) and 0.33 to 0.52 with
`importer` (none): today's quests pay for delivering goods, and none of them puts working capital
in the hands of broke miners and smiths. The planned answer is relief and loan quests (F2, M17),
the mechanism real economies use to escape a liquidity trap.
`test_fact_2_ore_prices_come_back_with_a_player` is a strict `xfail` that starts passing when one
works.

**For researchers:** don't use mine-disaster exports for post-shock price analysis, with or
without `--player`: after day 55, the iron ore price on most seeds reflects a frozen market.

### D2. Coin concentrates to real-world levels, but not through capital

Real wealth is highly concentrated: the global household wealth Gini was 0.92 in 2014, with the
top 10% holding 88% (Davies et al., 2017), and returns on capital, land and housing above all,
drive much of it (see [RESEARCH.md, M58](RESEARCH.md#m58-fairness-for-late-joiners)).

The baseline gets there slowly. Over 20 seeds its coin Gini is 0.27 ± 0.01 on day 120 and
0.49 ± 0.04 on day 365, above 0.5 on 14 seeds, with peaks from 0.26 to 0.70. But NPCs own no
capital: they can't buy land, lend or invest. So the concentration comes from somewhere else,
most likely differences in skill, thrift and profession compounding over time, and not yet
diagnosed. A researcher can use the *level* of inequality but should not read its *cause* as the
real-world one. Land and mine claims (M60) add a capital channel to measure against it.

**Tests:** `test_divergence_d2_early_on_coin_is_far_more_equal_than_real_wealth` checks the
first 120 days stay below 0.4, and `test_divergence_d2_over_a_year_coin_concentrates` checks
the Gini climbs over the year, so either change shows up here.

## References

**How these were found:** relevance-ranked searches with [Consensus](https://consensus.app), then
bibliographic metadata from [Crossref](https://www.crossref.org). Findings are taken from each
paper's abstract, not its full text; check the paper before relying on a number.

Chetty, R., Hendren, N., Kline, P., & Saez, E. (2014). Where is the land of opportunity? The
geography of intergenerational mobility in the United States. *The Quarterly Journal of
Economics, 129*(4), 1553-1623. https://doi.org/10.1093/qje/qju022

Davies, J. B., Lluberas, R., & Shorrocks, A. F. (2017). Estimating the level and distribution of
global wealth, 2000-2014. *Review of Income and Wealth, 63*(4), 731-759.
https://doi.org/10.1111/roiw.12318

Hill, R. V., & Fuje, H. (2020). *What is the impact of weather shocks on prices? Evidence from
Ethiopia* (Policy Research Working Paper No. 9389). World Bank.
https://doi.org/10.1596/1813-9450-9389

Hill, R. V., & Porter, C. (2017). Vulnerability to drought and food price shocks: Evidence from
Ethiopia. *World Development, 96*, 65-77. https://doi.org/10.1016/j.worlddev.2017.02.025

Kheyruri, Y., Sharafati, A., & Neshat, A. (2023). The socioeconomic impact of severe droughts on
agricultural lands over different provinces of Iran. *Agricultural Water Management, 289*,
108550. https://doi.org/10.1016/j.agwat.2023.108550

Letta, M., Montalbano, P., & Pierre, G. (2021). Weather shocks, traders' expectations, and food
prices. *American Journal of Agricultural Economics, 104*(3), 1100-1119.
https://doi.org/10.1111/ajae.12258

Stuermer, M. (2018). 150 years of boom and bust: What drives mineral commodity prices?
*Macroeconomic Dynamics, 22*(3), 702-717. https://doi.org/10.1017/S136510051600050X
