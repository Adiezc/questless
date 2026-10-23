# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
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
