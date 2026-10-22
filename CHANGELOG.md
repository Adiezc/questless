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

### Changed
- Dashboard: unmet demand is plotted as a share of demand from buyers who could pay (0-100%), so
  low-volume goods are as visible as food (M14.4, #14).

### Fixed
- Scenario files that set a number to `nan`, `inf` or `-inf` now fail to load with a clear
  "must be a finite number" error, instead of crashing partway through a run (#10, thanks
  @ElectLive).
- Guild treasury reports are taken after the day's contract escrow, so the dashboard's treasury
  card and chart agree (M13.3, #13).

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
