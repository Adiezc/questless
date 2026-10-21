# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
