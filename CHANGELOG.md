# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed
- Scenario files that set a number to `nan`, `inf` or `-inf` now fail to load with a clear
  "must be a finite number" error, instead of crashing partway through a run (#10, thanks
  @ElectLive).

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
