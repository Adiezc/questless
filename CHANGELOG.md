# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Land and mine claims (M60), off by default: `[claims] enabled = true` gives every gatherer the
  claim they work. A tenant pays the owner `rent_share` of the day's output value. An owner short
  of coin sells a claim to the richest NPC and rents it back. `TickStats` gains `claims` (rent,
  sales, the top decile's share of claims) and `wealth_gini` (coin plus claims at their price),
  and the export adds per-NPC `claims_owned`, `claim_value`, `rent_paid` and `rent_received`.
  Over a year on the baseline (20 seeds), trading claims raises the wealth Gini by
  0.063 ± 0.016 against claims that never trade, and makes wealth ranks stickier (day 30 against
  day 364: 0.56 against 0.46). Policy overlays may switch claims on
  (`experiments/stress/policies/claims.toml`).
- `docs/VALIDATION.md`: stylized facts from the literature, each checked on 5 seeds by
  `tests/test_stylized_facts.py`. Supply shocks raise prices, food prices recover after a
  drought, shortages cause hunger, and wealth ranks persist without being fixed. Two known
  divergences are tracked as strict `xfail`s or bounds: iron ore prices don't recover after the
  mine disaster (D1), and baseline coin reaches real-world concentration over a year without
  any capital to earn on (D2): right level, wrong cause.
- Research export, part 2: `--player local|importer` puts a scripted player in every run, so
  quests get delivered, and adds `player_days.csv` plus `player` and `player_profit` in
  `runs.csv`. `--transactions` writes every ledger entry to `transactions.csv` (about 600 rows a
  day). `ScriptedPlayer` moved from `experiments/shock_vs_baseline.py` to `questless.bots`. With a
  local player in every run of Iron Shortage (20 seeds), the top-decile levy no longer lowers the
  final Gini (−0.005 ± 0.019) and hunger rises by 11.7 ± 5.1 NPC-days, so a policy's effect
  depends on whether players are there.
- Percentile levy brackets: a `[[town.levy_brackets]]` entry can give `percentile = 0.9` instead
  of a fixed `threshold`, and each day's threshold becomes the NPC wallet at that rank. The fixed
  brackets in `progressive_levy.toml` (500 and 2,000 coin) only touched 0.8% of NPC-days on Iron
  Shortage; the new `levy_top_decile.toml` (6% above the 90th percentile, 10% above the 99th)
  lowers the final coin Gini by 0.029 ± 0.012 over 20 seeds, against 0.005 ± 0.002. Each day's
  resolved thresholds are in `TickStats.levy_thresholds` and the export's `daily.csv`.
- Research export: `questless export <scenario> [--policy <toml>]... --seeds 20 --out data/` runs
  the scenario and each policy arm on the same seeds and writes `daily.csv`, `npc_days.csv` (one
  row per NPC per day), `events.csv` (shocks and changed rules), `runs.csv` (with state hashes to
  rerun against) and a generated `codebook.md`. `experiments/analyse_export.py` is a worked
  example: on Iron Shortage over 20 seeds, the progressive levy lowers the final coin Gini by
  0.005 ± 0.002, and wealth ranks on day 30 and day 119 correlate at 0.36. The policy-overlay
  loader moved from `experiments/stress/policy.py` to `questless.policy` so the CLI can use it.
- Coin concentration (M58.1): each day records the Gini of NPC coin and the share held by the
  richest 10%, as `coin_gini` and `coin_top10_share` in `timeseries()`. On the baseline the Gini
  drifts from 0.23 to 0.18 over the first month. Guild, town and player accounts are left out.
- Exploit evidence (M52.4): for every exploit the hunt flags, `hunt.py` saves a replay to
  `experiments/results/exploits/` and lists the coin flows behind the gain, by who paid and who
  was paid. The hoarder on Iron Shortage (seed 9) took 1,261 coin from the blacksmiths' guild and
  individual smiths and spent 590 on miners and caravans.
- Planted-exploit test (M52.5) and a fourth attacker, the prober, which accepts every contract and
  tries to deliver it before sourcing anything. With a #43-style hole planted (a procurement
  contract that pays when nothing is delivered), the hunt flags the prober on every seed; on the
  shipped scenarios it finds nothing.
- Policy stress tests (M52.1, M52.3): a policy is a TOML file that `extends` a scenario and may
  change only its rules (town, contracts, legitimacy, transport fee, import markup, guild dues and
  policy); `policy.diff` lists what changed. `experiments/stress/hunt.py --policy <file>` plays
  every attacker and honest player before and after the policy on the same seeds and flags any
  attacker that wins on most seeds only after it. Example: a progressive levy on Iron Shortage
  opens no new exploit.
- Exploit hunters (M52.0): `experiments/stress/hunt.py` runs three scripted attackers (claim and
  wait, buy before a scheduled shock, accept and abandon) against two honest players on the four
  shock scenarios, 10 seeds each, and reports gain per day and the hunger each one adds. No
  large exploit: hoarding iron before Iron Shortage wins narrowly on 6/10 seeds and adds hunger;
  the others don't beat honest play. Results in `experiments/results/exploit_hunt.md`.
- Economy checks on every pull request (M23): `questless diff --base <ref>` runs every scenario
  on 10 seeds on the base commit (in a temporary git worktree, with its own engine) and on your
  working tree, then writes `economy-diff.md` and `.json`. Significant changes are listed in plain
  words; the check fails on broken invariants, on state-hash changes nothing explains, or on
  limits in `.questless/ci.toml`. The Economy workflows post the result as one comment per pull
  request, using the two-workflow pattern so fork code never gets a write token.
- Bug reports that replay themselves (M28.1, M28.2): `Simulation.bug_report(note, observation)`
  bundles the save with a checkable observation (metric, day, operator, value), and
  `questless repro bug.json` replays it and says **reproduced**, **not reproduced** or **replay
  mismatch** (exit 1, 0 and 2, ready for `git bisect run`).
- Scenario `legitimacy_spiral.toml` (M48.5): a town that starts with 300 coin and legitimacy on
  stays trapped, with legitimacy near 0.45, levy evasion and unpaid wages, on 10 of 10 seeds. The
  normally funded baseline with legitimacy on stays near 0.96 for a year with no unpaid days.
- Legitimacy and levy evasion (M48.1, M48.2), off by default. With `[legitimacy] enabled = true`
  the town's authority falls fast when guard wages go unpaid or NPCs go hungry and recovers slowly;
  while it is low, NPCs evade the upkeep levy and keep the coin, so nothing is created or
  destroyed. Recorded as `TickStats.legitimacy` and `TickStats.levy_evaded`.
- Economy diff core (M23.1, M23.2, M23.4): `questless.diff` measures a run (price index and
  shortage days per good, hungry NPC-days, recovery days, contracts posted and delivered, coin by
  sector, invariant failures), runs a scenario × seed grid in one or several processes with
  identical results, and compares two grids paired by seed, flagging only changes beyond
  seed-to-seed noise and at least 3%.
- Civilization DNA groundwork (M54.1): `questless.founding.mutate(cfg, rng)` returns a colony's
  config, nudging only the knobs listed in an optional `[founding.bounds]` table within their
  ranges, and `mutations(parent, child)` lists what changed. Only institutional knobs may be
  listed (levy, wages, market tax, guild dues and relief); the strict loader checks the result.
- Experiment: `experiments/late_joiners.py` runs the scripted player joining a fresh world and a
  world that has run 1,000 days, with the shock moved to the same point in the player's time, and
  compares them at equal days played (M58.2). First results: the old world doesn't treat a
  newcomer worse (first contract 2-4 days sooner, similar or higher profit with a wider spread).
- Progressive upkeep levy: optional `[[town.levy_brackets]]` (threshold, rate) above the flat
  `upkeep_rate`, each bracket taxing only the coin that falls in it (M58.3). Without brackets the
  levy and every state hash are unchanged.
- `causes.graph(world, contract)` and `Simulation.graph(contract_id)` export a quest's causal chain
  as JSON: evidence as nodes (with their sentence and measure keys) and cause-to-effect edges
  (M55.0). Ready for the map (M15) and the wiki (M25).
- CONTRIBUTING: "Giving everyone a turn". One claimed issue and one open pull request per
  person at a time, `good first issue` tasks kept for first-time contributors, and every bug fix
  needs a test shown to fail without the fix. The pull request template asks for both.
- Dashboard: a "Show as % of normal" toggle on the Economy tab plots prices and production
  relative to each good's average over days 10-14, with a dotted 100% line (M14.1, #15).
- Metrics: `price_index`, `produced_index`, `unfilled_pct` and per-guild `escrowed` series.
- Quests open with a one-sentence summary read off the evidence chain: root cause, key effect and
  who pays for what (M16.1). It only repeats numbers the chain recorded. `Simulation.summarise()`.
- Quest cards show an estimated profit: the reward minus the cheaper of buying the missing units
  at market or a caravan that arrives in time (M16.2). `Simulation.quote()` and the pure
  `quote_buy`, `quote_caravan` and `quote_contract` helpers expose the same numbers.
- Provenance: `series(world, key, start, end)` re-measures an evidence key day by day, and
  `Simulation.evidence_series(contract_id, step)` returns it for one chain step, so evidence charts
  show exactly the numbers `verify()` checks (M15.1).
- Dashboard: each measured fact in a quest's "Why?" chain is clickable. Picking one highlights it
  and charts it day by day from `evidence_series`, with its normal and threshold lines and the
  recorded value marked (M15.2).
- Run report: `questless.report` builds a summary of a run (production, hunger, live contracts,
  guild treasuries) and renders it as Markdown or a standalone offline HTML page with SVG
  sparklines (#29, thanks @RajGahoi).
- Dashboard: a grey warm-up band covers days 0-9, and shocks are drawn as neutral hatched bands
  labelled above the plot (M14.3, #26, thanks @RajGahoi).
- Roadmap and build guide: ten milestones from the #53 idea bank, with tasks, tests and
  pitfalls. v0.3 gains legitimacy and levy evasion (M48), beliefs and rumours (M49), policy stress
  tests (M52), unpaid guards turning bandit (M56) and amnesty and debt jubilee (M57); v0.4 the
  invisible border (M53), civilization DNA (M54) and infrastructure dependency maps (M55); v0.5
  told history versus the log (M50) and records that decay (M51).
- Research evidence for roadmap milestones (docs/RESEARCH.md), starting with M58, fairness for
  late joiners: findings by lever from 34 peer-reviewed papers, with APA references and DOIs.
- Research evidence for the proposed respectful-play milestone: what harms players (pressure to
  play, not hours played) and which levers help, from 27 peer-reviewed papers.
- Roadmap and build guide: M59, respectful play, in v0.3. Schedule bots (a grinder, a parent, a
  shift worker, a weekend player and a returner) and an economy check that fails when a change
  makes being away costlier or rewards streaks, appointments or short windows.

### Changed
- Dashboard: unmet demand is plotted as a share of demand from buyers who could pay (0-100%), so
  low-volume goods are as visible as food (M14.4, #14).
- Dashboard: guilds have their own colour set, and the treasury chart starts at zero (M14.5,
  #25, thanks @RajGahoi).
- Dashboard: the brand, day and time controls share one compact sticky header, and the intro
  text moved into the "How it works" tab (M14.6, #27, thanks @RajGahoi).
- Quest board: contract types use plain words ("Guild order", "Town order", "Transport job"), and
  pooled needs say which guild or town order covers them (M16.3, #22, thanks @RajGahoi).

### Fixed
- Research export: `npc_days.csv` counted the coin and goods of NPCs who work at the market
  (smiths) twice, because their work site is their own account. Wealth mobility on Iron Shortage
  is 0.36, not the 0.63 first reported.
- A player can no longer corner a good ahead of a shock (#93). The exploit hunt found that buying
  iron ore before the scheduled Iron Shortage out-earned honest play on most seeds and left smiths
  hungry. `Simulation.config` no longer shows the shock schedule; `Simulation.shocks()` lists
  shocks once they start, without saying how long they last. Hiding dates alone made it worse
  (buying on the announcement won on 12/20 seeds), so a player may now also buy at most
  `player.max_buy_share` (25% in the baseline) of a good's sellable stock each day. The hoarder
  now beats honest play on 3/20 seeds in Iron Shortage and none elsewhere.
- Pools no longer block members they give nothing to (M13.8, #46). A partly funded guild or town
  pool listed every short member, even those it gave 0 units, and suppressed their own contracts
  until it closed; so did members who ran short after the pool was posted. Pools now list only
  members who get units, and only those members count as covered. Over a 120-day run, needs
  suppressed as "covered by pool" fall from 1,204 to 208 in Mine Disaster and 315 to 109 in Iron
  Shortage. A guild may now fund its pool and a left-out member's own contract at the same time.
- The town no longer runs dry in long runs (M13.12, #72). Guard wages were 10-12 coin a day more
  than the levy and market tax brought in, so on seed 3 the treasury hit 0 by day 632 and guards
  went unpaid on 341 of 2,000 days. The baseline now has a reserve target: while the town holds
  less than `town.reserve_days` (10) days of wages, every levy rate rises by `town.reserve_rate`
  (2%) until it recovers. On seeds 1-5 over 2,000 days the town stays above 1,790 coin after day
  365 and no guard goes unpaid, with legitimacy on or off; so does Mine Disaster moved to day
  1,015. `reserve_days = 0` turns it off; `legitimacy_spiral.toml` does, to keep showing the trap.
- Saves of worlds whose guilds have no `max_treasury` load again; the absent ceiling was written
  as `None`, which the loader rejected.
- Guild treasuries no longer hoard the town's coin in long runs. A guild's coin above its new
  `policy.max_treasury` (3,000 in the baseline) pays the daily upkeep levy to the town, reported
  as `GuildReport.upkeep`. Over 2,000 days on seeds 42 and 7, unpaid guard days fall from 899 and
  1,211 to 0, and no guild holds more than 19% of all coin. Runs of 365 days are unchanged
  (M13.10, #48).
- Causal chains cite only shocks that cut output and overlap the shortage (allowing 7 days for
  stocks to run down), most recent first. A ×3 boom or a collapse that ended weeks earlier is no
  longer blamed for a later shortage, and quest summaries name the right event (M13.9, #47).
- Scenario files that set a number to `nan`, `inf` or `-inf` now fail to load with a clear
  "must be a finite number" error, instead of crashing partway through a run (#10, thanks
  @ElectLive).
- Player shocks with a `nan`, `inf` or `-inf` factor are rejected with a clear error before
  anything is scheduled, leaving the world unchanged (M13.2, #21, thanks @RajGahoi).
- Guild treasury reports are taken after the day's contract escrow, so the dashboard's treasury
  card and chart agree (M13.3, #13).
- `Simulation.step()` raises `ValueError` for a negative number of days instead of doing nothing,
  and unknown contract, NPC and guild ids raise `UnknownIdError` (a `KeyError`) with a plain
  message such as "unknown contract 'C-9999'" (M13.4, #24, thanks @ZeeEmn).
- Quest summaries name the good each quoted number belongs to, preferring the contract's own good,
  so an iron-ore contract no longer quotes the tools figures (M13.6, #50, thanks @Golden007-prog).
- When the town can't afford every guard's wage, the guards it pays rotate from day to day instead
  of the same ones always going unpaid (#52, thanks @jay23606).
- Transport contracts pay only for the units actually hauled; the unhauled share of the reward
  goes back to the funder, reputation scales the same way, and a contract with nothing left to
  haul can't be delivered. Quest cards estimate the reward from what is still there (M13.5, #43,
  #57, thanks @RajGahoi).
- A guild pool contract leaves out members who already have their own live contract for the same
  good, so no one is funded twice; the board check now fails if anyone is (M13.7, #45, #59,
  thanks @RajGahoi).

## [0.1.0] - 2026-10-21

First public prototype.

### Added
- **Engine** (stdlib only):
  - a 100-NPC settlement with farmers, miners, blacksmiths, merchants and guards;
  - one ledger with per-tick conservation checks;
  - a market with stock-and-flow pricing and an effort supply curve;
  - aggregate transport;
  - guild dues and working-capital relief;
  - a town levy and wages;
  - time-bounded shocks.
- **Contract engine:**
  - scarcity tracking, kept separate from poverty;
  - procurement, guild supply, town supply and transport contracts;
  - escrowed (and partial) funding, deduplication, cooldowns, caps, feasibility checks and a
    minimum reward;
  - expiry and withdrawal, plus outcome measurement after delivery.
- **Provenance:** a causal walk to root causes, evidence that `verify()` can re-measure, and
  quest lineage.
- **Player:** accept, buy, caravan, deliver, abandon and shock, all logged.
- **Saving:** save files that replay exactly, verified by a state hash.
- **Interfaces:** the `questless.Simulation` API and a CLI (`run`, `replay`, `demo`).
- **Scenarios:** baseline, iron shortage, mine disaster, drought, bandits (TOML with `extends`).
- **Dashboard:** Streamlit and Plotly (`demo` extra).
- **Experiments:** calibration report and a shock-vs-baseline experiment (`experiments` extra),
  with results in `docs/RESULTS.md`.
- **Tests:** 153 tests, including a chaos player, cross-process determinism, counterfactuals
  and multi-seed scenario checks.
- **Docs:** architecture, simulation spec, demo guide, plan and evaluation.

### Added (project docs and tooling)
- Public roadmap from v0.2 to v0.5 (docs/ROADMAP.md) and a build guide that splits every milestone
  into issue-sized tasks (docs/BUILD_GUIDE.md).
- Design documents: megaserver blueprint, crypto and blockchain assessment, privacy and identity,
  real-world skills, and the v0.1 stress-test review.
- Contributor guide, security policy, code of conduct, pull request and issue templates, and a
  security CI workflow (bandit, pip-audit, gitleaks) with Dependabot.

### Security
- Upgraded Pillow (a dependency of the dashboard and chart extras) from 12.3.0 to 13.0.0 to fix
  known vulnerabilities.
