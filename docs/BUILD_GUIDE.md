# Build guide: how each roadmap item gets built

This is the contributor's companion to [ROADMAP.md](ROADMAP.md). The roadmap says **what** each
milestone delivers and how we know it's done. This guide says **how** to build it: which files to
touch, in what order, which tests to write, and the traps to avoid.

- **New here?** Read [Part 1](#part-1-ground-rules) and [Part 2](#part-2-codebase-map), then pick a
  task marked **good first issue**.
- **Building a whole milestone?** Read its section in Part 4 and the recipes it links to in
  Part 3.
- **Estimates** are for someone who knows the codebase. Double them for a first contribution.

Everything here is a plan, not a spec carved in stone. If you find a simpler way that keeps the
guarantees, propose it in the issue before building it.

## Contents

- [Part 1: ground rules](#part-1-ground-rules)
- [Part 2: codebase map](#part-2-codebase-map)
- [Part 3: recipes for common changes](#part-3-recipes-for-common-changes)
- [Part 4: milestones, step by step](#part-4-milestones-step-by-step)
  - v0.2: [M13](#m13-bug-fixes) · [M14](#m14-readable-charts-and-compact-layout) ·
    [M15](#m15-clickable-evidence-and-map-highlight) · [M16](#m16-quest-summaries-profit-and-why-no-quests) ·
    [M17](#m17-relief-and-loan-quests-credit-scores) · [M18](#m18-futures-contracts) ·
    [M19](#m19-smuggling-and-black-markets) · [M20](#m20-central-bank) ·
    [M21](#m21-exportable-run-report) · [M22](#m22-experiments-and-docs-refresh)
  - v0.3: [M23](#m23-economy-checks-on-every-pull-request) · [M24](#m24-ai-agent-training-environment) ·
    [M25](#m25-self-writing-world-wiki) · [M26](#m26-economics-and-politics-lessons) ·
    [M27](#m27-docs-and-v030) · [M28](#m28-bug-reports-that-replay-themselves) ·
    [M29](#m29-courts-for-broken-contracts) · [M30](#m30-tamper-evident-world-log) ·
    [M31](#m31-one-person-one-character-safeguards) ·
    [M32](#m32-elections-and-a-campaign-finance-register) ·
    [M48](#m48-legitimacy-and-levy-evasion) · [M49](#m49-beliefs-and-rumours) ·
    [M52](#m52-policy-stress-tests) · [M56](#m56-unpaid-guards-turn-bandit) ·
    [M57](#m57-amnesty-and-debt-jubilee)
  - v0.4: [M33](#m33-theme-packs-and-world-topology) · [M34](#m34-regions-and-simulation-level-of-detail) ·
    [M35](#m35-a-map-shaped-by-the-economy) · [M36](#m36-ecology-and-the-commons) ·
    [M37](#m37-legal-automation-standing-orders) · [M38](#m38-players-post-quests) ·
    [M39](#m39-treaties-sanctions-and-embargoes) · [M40](#m40-surrogate-fast-forward-experiment) ·
    [M41](#m41-docs-both-skins-and-v040) · [M53](#m53-the-invisible-border) ·
    [M54](#m54-civilization-dna) · [M55](#m55-infrastructure-dependency-maps) ·
    [M58](#m58-fairness-for-late-joiners)
  - v0.5: [M42](#m42-privacy-as-code) · [M43](#m43-language-bridge) · [M44](#m44-steward-npcs) ·
    [M45](#m45-skills-passport) · [M50](#m50-told-history-versus-the-log) ·
    [M51](#m51-records-that-decay) · [M46](#m46-docs-and-v050)
- [Part 5: backlog ideas, sketched](#part-5-backlog-ideas-sketched)

---

## Part 1: ground rules

These are the guarantees every change must keep. CI enforces most of them. A pull request that
breaks one isn't mergeable, however good the feature.

| Rule | What it means in practice | Enforced by |
|---|---|---|
| **One ledger** | Every coin and good lives on a ledger account. Change balances only with `transfer`, `produce` or `consume` (and from M20, `mint`/`burn`). Never edit a balance directly. | `Ledger.check_conservation`, `tests/test_invariants.py` |
| **Escrow first** | An obligation (contract, loan, future, bounty) exists only after its coin is moved into escrow. | Invariant: escrow total == live obligations |
| **Evidence, not prose** | Every contract (and from v0.2, every loan, quote, mint, ruling) carries `Evidence` records. Measured values carry a `measure` key so `verify()` can recompute them. | `tests/test_provenance.py` |
| **Deterministic** | Use `world.rng.stream("<name>")`, never the `random` module, the clock or set ordering. Sort before iterating when order matters. | `tests/test_determinism.py` (two hash seeds) |
| **Replayable** | Player-side changes go through `player.apply_action`, with JSON-serialisable arguments, so they land in the action log. | Save → load → same state hash |
| **Knobs in TOML** | Numbers a designer might tune go in `scenarios/*.toml` via `config.py`, not in code. | Review |
| **Engine stays stdlib** | `src/questless/` imports only the standard library. Extras (`demo`, `gym`, ...) live in `app/`, `experiments/` or a module guarded by an optional import. | Review; `uv sync` without extras must pass tests |

Workflow: `uv sync --extra demo`, `uv run pytest`, `uv run ruff check .`,
`uv run ruff format .`. One change per pull request, with tests. See
[CONTRIBUTING.md](../CONTRIBUTING.md).

## Part 2: codebase map

```
src/questless/
  config.py            strict TOML loader: dataclasses, _parse(), to_dict() round trip, `extends`
  sim/
    ledger.py          Asset enum, Ledger (transfer / produce / consume, journal, conservation)
    entities.py        NPC, Guild, Site, Profession, account naming helpers
    world.py           World, TickStats, the daily tick loop, state_hash(), build_world()
    behaviour.py       one NPC's day: eat, repair, produce, decide what to buy and sell
    market.py          daily clearing, prices, rationing
    transport.py       hauling from sites to market
    guilds.py          dues, relief, treasury reports
    shocks.py          time-windowed modifiers on sites and transport
    alloc.py           seeded fair splitting and rationing
    rng.py             named, seeded RNG streams
  contracts/
    model.py           Contract, ContractKind, Status
    needs.py           NeedTracker: how long each need has gone unmet
    engine.py          ContractBoard: candidates → funder → evidence → validation → post; fulfil
    validation.py      the rules a contract must pass before posting
    provenance.py      Evidence, TEMPLATES, METRICS, measure(), verify()
    causes.py          the bounded causal walk back to root causes
  player.py            player actions (ACTIONS registry), ActionError
  persistence.py       save = scenario + action log + state hash; load = replay + hash check
  metrics.py           timeseries for charts
  api.py               Simulation facade (the public Python API)
  cli.py               `questless run | replay | demo`
app/                   Streamlit dashboard (streamlit_app.py, charts.py, theme.css)
experiments/           calibration, shock-vs-baseline experiment, charts, screenshots
scenarios/             baseline.toml and the shock scenarios that extend it
tests/                 unit/, integration/, and the guarantee tests at the top level
```

**The daily tick** (`World._tick`), in order. New mechanics must pick their slot deliberately:

1. Each NPC's day (`behaviour.run_npc_day`): eat, wear tools, produce.
2. Transport (`transport.ship`).
3. Town upkeep levy, then guard wages.
4. Guild relief (before the market, so relief buys food today).
5. Market clearing and prices.
6. Guild dues and treasury reports.
7. `TickStats` appended (everything charts and `verify()` read).
8. Needs tracker, then the contract board (expire, measure outcomes, generate).
9. `tick += 1`, caravans unload, invariants checked.

## Part 3: recipes for common changes

Most milestones are combinations of these. Each recipe lists every place you must touch; missing
one is the usual cause of a failing test.

### R1. Add a config knob

1. Add the field to the right dataclass in `config.py` (or a new `XConfig` dataclass and a field on
   `ScenarioConfig`).
2. Parse it in `_parse()` with the validating helpers (`_number`, `_fraction`, `_pos_int`, ...).
   Add the key to that section's `_keys(...)` list, or the strict loader will reject it.
3. Add it to `to_dict()` so saves round-trip.
4. Give it a value in `scenarios/baseline.toml`. New features default to **off** in the baseline so
   v0.1 results stay comparable.
5. Tests: `tests/unit/test_config.py` (valid value, invalid value raises `ConfigError`), and the
   existing round-trip test must still pass.

### R2. Add a new account or flow of money

1. Name it with a helper in `entities.py` (like `guild_account`).
2. Open it in `build_world()` **before** the ledger is sealed.
3. Move coin or goods with `ledger.transfer(..., reason="<short reason>")`. Reasons appear in the
   journal and in reports, so make them readable.
4. If the account holds money that "belongs" to obligations (escrow, collateral), add an invariant
   to `World.check_invariants()` that ties its balance to the open obligations.
5. Add the account's balance to `TickStats` if charts need it (R6).

### R3. Add a new evidence kind

1. Add a sentence template to `TEMPLATES` in `provenance.py` and the kind to the comment list on
   `Evidence.kind`.
2. If the value can be recomputed, add a function to `METRICS` and set `measure=(key, tick)` when
   you create the evidence. Prefer measurable evidence: it's what makes the chain trustworthy.
3. Create the evidence where the decision is made (contract engine, loan desk, central bank), and
   link it with `caused_by` to earlier evidence in the same chain.
4. If it can be a root cause, teach `causes.py` how to walk to it.
5. Tests: `verify()` passes on a real run, and a forged value (edit `value` with
   `dataclasses.replace`) is reported.

### R4. Add a new contract kind

1. Add it to `ContractKind` in `model.py`.
2. Produce candidates in `engine._candidates()` (or a new generator called from
   `ContractBoard.generate`).
3. Pick the funder (`_choose_funder`) and build evidence (`_evidence`).
4. Make sure `validation.py` covers it: funded, deduplicated, cooled down, capped, feasible.
5. Handle fulfilment in `ContractBoard.fulfil` (what moves where) and outcomes in
   `measure_outcomes`.
6. Dashboard: a label in `kind_label()` and plain wording on the card.
7. Tests: a scenario that produces it, the counterfactual (same seed without the cause produces
   none, see `tests/test_economic_justification.py`), and invariants under a chaos player.

### R5. Add a player action

1. Write `def my_action(world, ...)` in `player.py`. Check everything first and raise
   `ActionError` **before** changing any state.
2. Register it in `ACTIONS`. `apply_action` logs it automatically; arguments must be
   JSON-serialisable (strings and numbers, not objects).
3. Expose it on `Simulation` in `api.py`, and in the CLI or dashboard if users need it.
4. Tests: happy path, each rejection leaves `state_hash()` unchanged, and save → load reproduces
   the hash after the action.

### R6. Add a statistic and a chart

1. Add a field to `TickStats` in `world.py` and fill it in `_tick()`.
2. Expose it in `metrics.timeseries()`.
3. If it can appear in evidence, add a `METRICS` entry (R3).
4. Chart it in `app/charts.py`, following the house rules: one axis, indexed or small multiples
   for mixed scales, neutral shock bands, legend for 2+ series.
5. Remember `state_hash()`: decide whether the new field is state (hashed) or a derived statistic
   (not hashed). Statistics derived from state shouldn't change the hash.

### R7. Add a scenario

1. Create `scenarios/<name>.toml` with `extends = "baseline.toml"` and only the overrides.
2. Add it to the scenario list in `tests/integration/test_scenarios.py` and to
   `experiments/calibrate.py` with target ranges.
3. Document it in `docs/SIMULATION_SPEC.md`.

### R8. Add an optional extra (a non-stdlib dependency)

1. Add it under `[project.optional-dependencies]` in `pyproject.toml` and refresh `uv.lock`.
2. Import it only inside the module that needs it, and raise a clear message if it's missing:
   "install with `uv sync --extra gym`".
3. Tests that need it use `pytest.importorskip("<package>")`, so the core test run still passes
   without extras.

---

## Part 4: milestones, step by step

Each milestone lists **where** the work lives, **tasks** sized to one pull request each (S = under
1 h, M = 1-3 h, L = 3+ h), the **tests** that prove it, and **pitfalls**. Task ids (M17.3) are meant
to become GitHub issue titles.

### M13: bug fixes

**Where:** `config.py`, `player.py`, `sim/world.py`, `api.py`, `app/streamlit_app.py`.

| Task | Size | How |
|---|---|---|
| M13.1 Reject NaN and infinity in config **(good first issue)** | S | In `config._number`, after converting, `if not math.isfinite(x): raise ConfigError(f"{where}: must be a finite number")`. Every numeric helper goes through it. |
| M13.2 Reject NaN and infinity in `player.shock` **(good first issue)** | S | Same check, raising `ActionError` before anything is scheduled. |
| M13.3 Treasury after escrow | S | Move the `guild_reports(...)` call after `self.contracts.step(self)` in `_tick`, or add an `escrowed` field per guild to the report. The second is safer: it doesn't change existing numbers. |
| M13.4 Clear errors for bad input **(good first issue)** | S | `Simulation.step(days)` raises `ValueError` for `days < 0`; `contract()`, `npc()` and `guild()` raise `KeyError` subclasses with "unknown contract 'C-9999'" messages. |

**Tests:** `factor = nan` and `inf` in TOML raise `ConfigError`; `sim.shock(..., factor=float("nan"))`
raises `ActionError` and leaves the state hash unchanged; the dashboard's treasury card equals the
chart's last point (a unit test on the numbers both read).

**Pitfalls:** `math.isfinite` on an `int` is fine, but booleans are ints in Python; keep the
existing bool rejection before the finiteness check.

### M14: readable charts and compact layout

**Where:** `app/charts.py`, `app/streamlit_app.py`, `app/theme.css`, `metrics.py`.

| Task | Size | How |
|---|---|---|
| M14.1 Index series to "% of normal" | M | In `metrics.timeseries`, add `*_index` series: value ÷ mean of days 10-14 (after warm-up, before any shock) × 100. Charts plot the index with a 100% reference line. |
| M14.2 Small multiples option | M | A toggle that draws one compact chart per good (Plotly `make_subplots`, shared x-axis, independent y). |
| M14.3 Warm-up band and neutral shock bands **(good first issue)** | S | Grey band for days 0-9; shocks as a hatched neutral band with the label in the top margin (`yref="paper"`, `y=1.02`). |
| M14.4 Unmet demand as % of demand | S | Divide by demand from `TickStats.market`; guard against division by zero. |
| M14.5 Guild colours and zero-based treasury axis **(good first issue)** | S | A separate guild palette (validated for colour-blind contrast), `rangemode="tozero"`, escrow as a lighter stacked band (needs M13.3). |
| M14.6 Compact sticky header | M | One horizontal container with brand, day, time buttons and the shock menu; sticky via CSS on the container's test id. Move the intro text into the "How it works" tab. |

**Tests:** a unit test that index series equal 100 on average over the reference window; the
Streamlit `AppTest` run still has 0 exceptions to day 360. Check visually at 1280 px.

**Pitfalls:** Streamlit test ids change between versions; pin the selector in one place in
`theme.css` with a comment.

### M15: clickable evidence and map highlight

**Where:** `app/streamlit_app.py` (chain panel and map), `app/charts.py`, `contracts/provenance.py`.

| Task | Size | How |
|---|---|---|
| M15.1 Metric series from a measure key | M | New `provenance.series(world, key, start, end)` that calls `measure(world, key, t)` for each day. Reusing `measure` guarantees the chart and the chain agree. |
| M15.2 Clickable chain steps | M | Render each measured step as a button; store the selected index in `st.session_state`; the evidence chart plots `series(...)` with baseline and threshold lines from that `Evidence`. |
| M15.3 Ring requester and beneficiaries on the map | S | Extra scatter trace with open circles at those NPCs' positions. |
| M15.4 Pulse the shocked site | S | A larger, semi-transparent marker at the site while a shock is active (CSS animation isn't available inside Plotly; use size and opacity). |
| M15.5 Road thickness and stockpile gauges | M | Line width from `TickStats.transport` units shipped today; a small bar per site from its stockpile account. |

**Tests:** for each measured step in the Iron Shortage contract, `series(...)[step.tick]` equals
the step's value (this is the milestone's acceptance test, and it runs without the UI).

### M16: quest summaries, profit and "Why no quests?"

**Where:** new `contracts/summary.py`, `app/streamlit_app.py`, `contracts/needs.py`.

| Task | Size | How |
|---|---|---|
| M16.1 One-sentence summary | M | `summarise(world, contract) -> str` picks the root, the key middle step and the funding step from the chain and fills a template: "The mine collapsed 14 days ago. Smiths ran out of ore. The Blacksmiths Guild will pay 363 coin for 31 ore." Only uses chain data, never new numbers. |
| M16.2 Estimated profit on cards | S | `reward - min(caravan cost, market cost for qty)`; reuse the cost functions in `player.py` without executing them (add a pure `quote_*` helper). |
| M16.3 Plain wording **(good first issue)** | S | Rename labels in `kind_label()`: "Guild order", "Transport job", "Town order". |
| M16.4 "Why no quests?" panel | M | `needs.suppressed(world)` returns needs that didn't post, grouped by reason (cooldown, cap, infeasible, poverty). Show the counts and today's unaffordable demand. |

**Tests:** summary text contains only numbers that appear in the chain; Mine Disaster day 149
returns a non-empty poverty explanation.

### M17: relief and loan quests, credit scores

**Where:** new `src/questless/finance/` package (`obligations.py`, `credit.py`, `loans.py`),
`contracts/engine.py`, `player.py`, `config.py`, `sim/world.py`.

**Design in one paragraph:** an **obligation registry** records who owes what to whom and when.
Each obligation is backed by coin in an escrow-like account, so conservation holds. Relief
contracts move coin or tools to poverty-trapped NPCs, funded by the town or a guild. Loans are
obligations with a schedule; repayments come out of the borrower's income automatically (a
standing transfer each day after wages and sales); missed payments are recorded with evidence and
lower a credit score.

| Task | Size | How |
|---|---|---|
| M17.1 Obligation registry | L | `Obligation(id, debtor, creditor, principal, rate, schedule, collateral_account, status)`. Methods: `open`, `due_today`, `settle`, `default`. Stored on `World`, included in `state_dict()`. |
| M17.2 Poverty evidence | M | New evidence kind `poverty` (R3): unaffordable demand vs income over 7 days, measurable from `TickStats`. |
| M17.3 Relief contract kind | M | R4. Candidate when an NPC's need is poverty, not scarcity, for N days. Funder: their guild, else the town. Fulfilment: the player delivers tools or coin; the funder's escrow pays the player a fee. |
| M17.4 Loan contract kind | L | R4 + R5. The player offers terms (`lend(npc_or_guild, amount, rate, days)`); the principal moves from the player to the borrower via the registry. Repayment runs in a new tick slot after market clearing. |
| M17.5 Credit score | M | `credit.score(entity)` from repayment history (on-time share, defaults, current debt ÷ income). Deterministic, no RNG. Shown on loan cards. |
| M17.6 Scripted lender in experiments | M | Extend `ScriptedPlayer` in `experiments/shock_vs_baseline.py` with a lending policy; add an arm. |

**Tests:** conservation with loans open across save/load; a default produces evidence that
`verify()` re-checks; credit score falls after a default; the Mine Disaster lender arm recovers on
at least 5 of 10 seeds (or the result is documented honestly).

**Pitfalls:** interest creates no coin; it's a transfer from borrower to lender. A borrower who
can never repay is the poverty trap again, so cap total debt by income.

### M18: futures contracts

**Where:** new `finance/futures.py`, `finance/market_maker.py`, `sim/behaviour.py` (hedging),
`player.py`, `app/` (Futures tab).

| Task | Size | How |
|---|---|---|
| M18.1 `Future` and its escrow | L | Dataclass from the roadmap. Opening moves `qty × strike` from buyer to a `futures_escrow` account and 30% collateral from the seller. Uses the M17 registry for the seller's delivery obligation. |
| M18.2 Settlement and default | L | On `delivery_tick`, in a tick slot after production and before market clearing: deliver goods, release escrow; on failure, compensate from collateral and record a default (M17 credit). |
| M18.3 Forward quotes | M | Merchants Guild quotes 10/20/30-day forwards with the roadmap formula. Each quote stores its inputs as evidence. Exposure cap from its treasury. |
| M18.4 NPC hedging | M | In `behaviour.py`, smiths and miners place bounded orders through the same functions players use. All randomness from a `hedging` RNG stream. |
| M18.5 Player actions | M | `buy_future`, `sell_future`, `close_position` (R5). |
| M18.6 Futures tab | M | Quote board, positions, mark-to-market P&L, settlement history. |

**Tests:** escrow == open notional + collateral every day (new invariant); settlement and default
paths; determinism with positions open across save/load; paired-seed test that hedged smiths have
fewer idle days.

**Pitfalls:** don't let futures settle in cash by accident; the design is physical delivery, which
keeps goods conserved and makes the economics honest.

### M19: smuggling and black markets

**Where:** new `sim/smuggling.py`, `contracts/engine.py` (two kinds), `entities.py` (faction
account), `sim/world.py`, `app/`.

| Task | Size | How |
|---|---|---|
| M19.1 Smuggler faction and trigger | M | Account opened at build time (empty). Activates when the roadmap's conditions hold 3+ days; evidence cites them. |
| M19.2 Contraband trade | L | A tick slot after market clearing: sell from `outside` stock at 1.5× to NPCs with unfilled demand. Bypasses tax and transport capacity. Seeded interception per shipment from a `smuggling` RNG stream. |
| M19.3 Lawlessness index | S | Smuggled volume and lost tax over 30 days, in `TickStats` and `METRICS`. |
| M19.4 Enforcement and run contracts | L | Two kinds (R4). Enforcement is town-funded; runs are smuggler-funded. |
| M19.5 Reputation per faction and guild | M | Generalise reputation to a map `{faction: score}`; effects differ by guild as the roadmap describes. |
| M19.6 Map and badges | M | Dashed routes, "Illicit" badge, lawlessness gauge. |

**Tests:** no smuggling in the baseline across 10 seeds; smuggling appears in Bandits and Drought
within 7 days; more enforcement means less volume (paired seeds); reputation changes match actions.

### M20: central bank

**Where:** `sim/ledger.py` (mint/burn), new `finance/central_bank.py`, `sim/world.py` (CPI, policy
slot), `config.py`, new `scenarios/monetary.toml`, `app/`.

| Task | Size | How |
|---|---|---|
| M20.1 Mint and burn in the ledger | M | Two new `EntryKind`s, allowed only for the `central_bank` account. Track `minted` and `burned` totals; conservation becomes `genesis + minted - burned` for coin. |
| M20.2 CPI and inflation | M | Basket = average consumption over the first 30 days at base prices; CPI = basket cost at today's prices ÷ at base. In `TickStats` and `METRICS`. |
| M20.3 Policy rule | L | Once a day after market clearing: compare CPI inflation with the target band and the broke-NPC share; decide mint/burn amounts and the policy rate within caps. Every decision is a `monetary_policy` evidence record. |
| M20.4 Rate transmission | M | Loans (M17), futures carry (M18) and guild relief read the policy rate. |
| M20.5 Discount window | M | Guild emergency borrowing via the M17 registry at rate + penalty. |
| M20.6 Lobby action and dashboard panel | M | `lobby(guild, direction)` (R5) spends reputation to nudge the rule's target within a bounded range. |

**Tests:** new conservation identity every day; caps hold under extreme shocks; 2,000-day drift
within ±25% with the bank on; every mint and burn re-verifies.

**Pitfalls:** feedback loops can oscillate. Use a smoothed CPI (30-day) and a maximum daily change
in the rate.

### M21: exportable run report

**Where:** new `src/questless/report.py` (stdlib only: string templates and hand-written SVG),
`cli.py`, `app/`.

| Task | Size | How |
|---|---|---|
| M21.1 Report model | M | `build_report(world) -> dict` with every section's data. Reused by the wiki (M25) and the economic report (M26). |
| M21.2 Markdown and HTML renderers | M | Small SVG line-chart helper (polyline in a viewBox); no external JS, so it opens offline. |
| M21.3 CLI and download button **(good first issue after M21.2)** | S | `questless report <scenario|save> --out report.html`; `st.download_button` in the dashboard. |

**Tests:** a report for each scenario renders, contains every contract id, and every chain in it
re-verifies.

### M22: experiments and docs refresh

**Where:** `experiments/`, `docs/`.

| Task | Size | How |
|---|---|---|
| M22.1 New experiment arms | M | Relief/loans, hedging, enforcement, central bank on/off. Each is a config override, so arms stay data, not code. |
| M22.2 One-command regeneration | S | `uv run python experiments/run_all.py` regenerates CSVs, charts and the tables in RESULTS.md. |
| M22.3 Docs and tag | M | RESULTS, README, SIMULATION_SPEC, CHANGELOG; tag v0.2.0. |

### M23: economy checks on every pull request

**Where:** new `src/questless/diff.py`, `cli.py` (`questless diff`), `.github/workflows/economy.yml`,
`.questless/ci.toml`.

| Task | Size | How |
|---|---|---|
| M23.1 Metric suite | M | `suite_metrics(world) -> dict[str, float]`: price index per good, hungry NPC-days, shortage days, recovery days, contracts posted/delivered, coin by sector, invariant failures. |
| M23.2 Run grid | M | `run_grid(scenarios, seeds, days)`; parallel with `concurrent.futures.ProcessPoolExecutor` (stdlib). |
| M23.3 Base vs head | M | `questless diff --base origin/main`: `git worktree add` the base into a temp dir, run the grid there with `uv run` and here, pair by (scenario, seed). |
| M23.4 Significance | S | Paired differences; flag when \|mean\| > 2 × standard error and the change exceeds a minimum effect (say 3%). Everything else reads "no significant change". |
| M23.5 Markdown comment | S | Headline bullets in plain words, then a collapsible table. |
| M23.6 GitHub Action | M | `on: pull_request` with `paths:` filters; `fetch-depth: 0`; run the diff; post or update one comment with `gh pr comment --edit-last` (fall back to creating one); upload charts as artifacts. Needs `permissions: pull-requests: write`. |
| M23.7 Gates in `ci.toml` | S | Limits like `hunger_ratio_max = 1.2`; breaking one fails the job with the evidence. |
| M23.8 Determinism check | S | For scenarios the PR didn't change, compare state hashes if the engine is unchanged; mismatch = red check. |

**Tests:** a fake "head" that halves farm output is flagged on hunger; identical trees report no
significant change; the significance function on known data.

**Pitfalls:** pull requests from forks get a read-only token. Use the two-workflow pattern (run
the diff on `pull_request`, post the comment from a `workflow_run` job) so secrets are never
exposed to fork code.

### M24: AI-agent training environment

**Where:** new `src/questless/gym/` (`env.py`, `spaces.py`, `impact.py`, `baselines.py`),
optional extra `gym`, `docs/AGENTS.md`.

| Task | Size | How |
|---|---|---|
| M24.1 Impact score | M | `impact.score(world)`: replay the same seed and scenario with no player actions (determinism makes this exact) and compare hungry NPC-days, shortage days, bankruptcies and local producers' sales. Shared with the backlog's impact ledger. |
| M24.2 Observation and action spaces | M | Fixed-size: the top K open contracts (pad with zeros), prices, stocks, wallet; evidence encoded as (kind id, metric id, value, baseline, threshold, age). Actions as `MultiDiscrete([verb, target, good, qty_bucket])` plus an action mask. |
| M24.3 `QuestlessEnv` | M | `reset(seed)` builds the world; `step(action)` maps to `apply_action` and advances one day; reward = change in impact score; `terminated` at the scenario's end. |
| M24.4 Text mode for LLM agents | S | `render_mode="text"` returns the board and chains as prose; actions accepted as JSON strings. |
| M24.5 "Explain" task | M | `QuestlessExplain-v0`: show a contract with its chain hidden; the agent answers with a root-cause kind and subject; score against the real chain. |
| M24.6 Baselines and leaderboard | M | Random, scripted, greedy; results table in `docs/AGENTS.md`; submissions are save files that anyone can replay. |

**Tests:** `gymnasium.utils.env_checker.check_env`; same seed + actions → same rewards; scripted
beats random on impact.

**Pitfalls:** recomputing the no-player baseline every step is expensive; cache it per (scenario,
seed) because it never changes.

### M25: self-writing world wiki

**Where:** new `src/questless/wiki/` (`visibility.py`, `redact.py`, `pages.py`, `vault.py`),
`cli.py` (`questless wiki`).

| Task | Size | How |
|---|---|---|
| M25.1 Visibility tags | M | `Visibility = PUBLIC | PLAYER | DEV`. A table in `visibility.py` maps every field and evidence kind to a tier; anything not listed is `DEV`. |
| M25.2 Redacted views | L | `public_view(world)` and `player_view(world, player_id)` build plain dicts containing only allowed fields. Renderers receive a view, never the `World`, so a renderer *can't* leak what it never sees. |
| M25.3 Page templates | M | One template per page type (npc, guild, site, good, shock, contract, digest): YAML front matter + short prose + `[[links]]`. Links to entities hidden from the tier render as "unknown". |
| M25.4 Salience rules | S | Who gets a page: appears in a chain, a guild/site/shock, or crossed a threshold (bankruptcy, record price). Everyone else goes into digests. |
| M25.5 Vault writer | M | Sharded paths (`npc/03/npc-0342.md`), incremental writes (only changed pages, by content hash), monthly roll-up of digests older than 90 days. |
| M25.6 Leak test | M | Plant unique marker strings in every private field (wallets, traits, seeds, smuggler ids), build the public vault, grep it: zero hits. This test is the milestone's core. |
| M25.7 Developer roles **(prepares M42)** | M | Split `DEV` into roles (`designer`, `liveops`, `safety`, `security`) in `visibility.py`; one vault per role; an access log file appended on every read through the CLI. |

**Tests:** the leak test; size budget (2 KB per page, under 5 MB for a 365-day run); every link
resolves or renders "unknown"; regenerating from a save gives byte-identical pages.

**Pitfalls:** aggregates can leak private data too (a "guild average wallet" over one member is
that member's wallet). Rule: public aggregates need at least 5 contributors.

### M26: economics and politics lessons

**Where:** new `src/questless/teach/` (`moments.py`, `lessons/`, `economic_report.py`),
`docs/TEACHING.md`, `app/` (guided mode).

| Task | Size | How |
|---|---|---|
| M26.1 Monthly economic report | M | Built on `build_report` (M21) with a public view (M25): money supply, faucets and sinks, price index, trade routes, who profited from each crisis, how players behaved. |
| M26.2 Moment finders | M | Pure functions that scan a run for a lesson's moment, e.g. `find_entitlement_famine(world)`: days where food was in stock but hungry NPCs couldn't afford it. Each returns evidence or `None`. |
| M26.3 Lesson format | S | A Markdown file per lesson with front matter (concept, scenario, moment finder, question, lever, answer metric) and a body with `{placeholders}` filled from the moment. |
| M26.4 Eight lessons | L | The roadmap's table. Each one is a good first issue for someone with an economics background once M26.2-M26.3 exist. |
| M26.5 Guided mode | M | Dashboard walk-through: show the moment, ask the question, let the player pull the lever, show the measured answer. |

**Tests:** each moment finder either finds its moment on every seed of its scenario or reports
none; every number in a rendered lesson re-verifies.

**Pitfalls:** don't overclaim. Each lesson ends with a "What the model leaves out" box.

### M27: docs and v0.3.0

README sections with one-command examples, `docs/AGENTS.md`, `docs/TEACHING.md`, changelog, tag.

### M28: bug reports that replay themselves

**Where:** new `src/questless/bugreport.py`, `cli.py` (`questless bugreport`, `repro`, `bisect`),
`app/` (Report a bug button), `.github/ISSUE_TEMPLATE/bug_report.yml`.

**Design:** a bug report is a save file (scenario + action log + state hash, about 9 KB a year)
plus what the reporter saw, written as a machine-checkable **observation**. Reproducing a bug is
then a command, not a conversation.

```json
{
  "format": "questless-bug/1",
  "save": { "...": "the normal save file" },
  "environment": {"questless": "0.3.0", "commit": "a1b2c3d", "python": "3.12.7", "os": "darwin"},
  "note": "Tools price stuck at ceiling after the mine reopened",
  "observation": {"metric": ["price", "tools"], "tick": 74, "op": ">=", "value": 60.0}
}
```

| Task | Size | How |
|---|---|---|
| M28.1 Report writer | M | `Simulation.bug_report(note, observation=None)` and a dashboard button that pre-fills the observation from the chart the user is looking at. |
| M28.2 `questless repro` | M | Replays the save, checks the hash, evaluates the observation with `provenance.measure`. Outcomes: **reproduced**, **not reproduced** (probably fixed), **replay mismatch** (the engine changed since the report). |
| M28.3 Version pinning | S | On mismatch, print the exact command to replay with the reporter's version: `uv run --with questless==0.3.0 questless repro bug.json` or a `git worktree` at the recorded commit. |
| M28.4 `questless bisect` | M | Wraps `git bisect run questless repro bug.json --quiet` between a good and bad ref, so the commit that introduced the bug is found automatically. |
| M28.5 Regression test from a report **(good first issue after M28.2)** | S | `questless repro bug.json --emit-test` writes `tests/regressions/test_<id>.py` that asserts the fixed behaviour. |
| M28.6 Issue template | S | `bug_report.yml` asks for the file and shows the `repro` command. |
| M28.7 Checkpoints (stretch) | L | For very long runs, store a full state snapshot every N days so replay starts from the nearest checkpoint. Needs a `World.from_state()` constructor; the hash check still guards it. |

**Tests:** a report of a planted bug reproduces; after the fix, it reports "not reproduced"; a
tampered save reports "replay mismatch"; bisect finds the planted commit in a test repo.

**Privacy:** in a live game, bug reports are dev-tier (M25); player ids are pseudonymous.

### M29: courts for broken contracts

**Where:** new `src/questless/law/` (`terms.py`, `claims.py`, `remedies.py`, `court.py`,
`precedent.py`), `contracts/model.py` (terms), `player.py`, `app/` (Court tab).

**Design:** contracts get explicit **terms**. When a party thinks the terms were broken, they file
a **claim**. Evidence comes only from the ledger and provenance, so every fact in a case can be
re-verified. Clear cases are decided automatically; contested ones go to an NPC magistrate and,
in multiplayer settings, a jury of players. The legal ideas below are simplified versions of real
contract-law concepts, chosen because the engine can measure them. It's a game system, not legal
advice.

**Real legal concepts and how each maps onto the engine:**

| Concept | Real-world idea | In Questless |
|---|---|---|
| Offer, acceptance, consideration | A contract needs an offer, its acceptance and something of value exchanged | Posting, `accept`, and the escrowed reward. Already there; M29 makes the terms explicit. |
| Security | A creditor holds collateral so the debt gets paid | Escrow, and a new **performance bond** the player posts on accepting large contracts |
| Breach | Failing to do what the contract says | Late, short or abandoned delivery; detected from the ledger |
| Expectation damages and "cover" | The wronged party gets what they'd have had; a buyer may buy substitutes and claim the extra cost (the US UCC calls this "cover") | Damages = cost of buying the missing goods at the spot price minus the contract price, measured from `TickStats` |
| Liquidated damages | A fixed penalty agreed in advance, if it's a reasonable estimate rather than a punishment | Optional term: a fixed penalty, capped at a share of the reward |
| Duty to mitigate | The wronged party can't let losses pile up | Damages are cut if the requester could have bought the goods at market and didn't |
| Force majeure, impossibility | Performance is excused when an outside event makes it impossible | A verified shock (bandits, no caravan stock) excuses the breach; the chain is the proof |
| Burden and standard of proof | The claimant must prove their case "on the balance of probabilities" | The claim must cite evidence that `verify()` confirms; unverifiable claims fail |
| Limitation period | Claims must be brought within a time limit | Claims allowed within N days of the breach |
| Costs rules | Who pays legal costs: "loser pays" (English rule) or each side pays its own (American rule) | A filing fee and a config switch between the two; a teaching point in M26 |
| Recusal | A judge or juror with a conflict of interest steps aside | Jurors who share a guild or a trading history with a party (found from the ledger) are excluded |
| Appeal and precedent | Higher courts review; past decisions guide future ones | One appeal to a higher-reputation panel; rulings published to the public wiki (M25) as case law and cited by later rulings |
| Enforcement and exempt property | Judgements are collected from assets, but debtors keep the essentials | Paid from the bond, then the wallet up to a limit, then recorded as debt (M17); the player keeps starter tools |

| Task | Size | How |
|---|---|---|
| M29.1 Contract terms | M | `Terms(deadline, qty, partial_allowed, bond, liquidated_damages)` on `Contract`; shown on cards; part of `state_dict()`. |
| M29.2 Breach detection | M | On expiry or abandonment, compute what was owed vs delivered and record `breach` evidence. |
| M29.3 Claims and the small-claims rules engine | L | `file_claim(contract_id, claimant)` (R5) with a fee. Clear cases (no excuse, measurable damages) are decided automatically: damages = cover cost or liquidated damages, reduced for failure to mitigate, cancelled by a verified force majeure. |
| M29.4 NPC magistrate | M | Contested cases (an excuse is claimed) are decided by a deterministic rule that weighs the verified evidence; the ruling is an evidence chain. |
| M29.5 Player juries (stretch, multiplayer) | L | Jurors drawn with a `court` RNG stream from eligible players, conflicts excluded, paid from fees, majority vote; votes are logged actions so cases replay. |
| M29.6 Enforcement | M | Bond → wallet (with an exemption floor) → debt in the M17 registry; credit score impact. |
| M29.7 Precedent pages | S | Each ruling becomes a wiki page (public tier, parties pseudonymous) with the facts, rule applied and outcome. |

**Tests:** a late delivery during a verified bandit shock is excused; the same delay without a
shock gives damages equal to the measured cover cost; the costs rule switch changes who pays the
fee; conservation holds through judgements; rulings replay exactly.

**Pitfalls:** frivolous claims (fee handles it), collusive claims between a player's own
characters (M31 detects shared ownership), and juror collusion (flag jurors whose votes correlate
with one party across cases).

### M30: tamper-evident world log

**Where:** `sim/ledger.py` (hash chain), new `src/questless/audit.py`, `cli.py` (`questless audit`).
See [BLOCKCHAIN.md](BLOCKCHAIN.md) for why this is built **without** a blockchain.

| Task | Size | How |
|---|---|---|
| M30.1 Hash-chained journal | M | Each day, hash `(previous root, sorted journal entries of the day, state hash)` with SHA-256 into a daily root. Changing any past entry changes every later root. |
| M30.2 Merkle proofs for accounts | M | Build a Merkle tree over sorted account balances each day; a player can be given a proof that their balance is in that day's root without seeing anyone else's. |
| M30.3 Commit-reveal for shocks | S | Scheduled shocks are published in advance as `sha256(shock spec + salt)` and revealed when they fire; `audit` checks the reveal matches. |
| M30.4 `questless audit` | S | Recomputes the chain from a save and reports the first day that doesn't match. |
| M30.5 Optional public anchor | S | An interface `Anchor.publish(day, root)` with a file-based implementation; a studio could publish roots on a website, a transparency log or a public chain. No chain dependency in this repo. |

**Tests:** editing one journal entry in a save is detected on that day; Merkle proofs verify; a
changed shock fails the reveal check.

### M31: one-person-one-character safeguards

**Where:** new `src/questless/integrity/` (`graph.py`, `signals.py`), `experiments/multibox.py`.

The engine can't verify real people (that's account and payment infrastructure), but it can make
multiboxing and bots **pointless and visible** inside the economy.

| Task | Size | How |
|---|---|---|
| M31.1 Multiple players in the engine | L | Generalise the single `player` account to `player:<id>`; actions carry the player id. Needed by M29 juries too. |
| M31.2 Bot league | M | N scripted players with different policies, some deliberately colluding (alts feeding a main), run in `experiments/multibox.py`. |
| M31.3 Transfer graph signals | M | From the ledger: one-sided trades at off-market prices, circular flows, accounts that only ever trade with one other account, contracts accepted and abandoned in patterns that move value. Each flag is an evidence chain. |
| M31.4 Behaviour signals | M | Action timing regularity, identical action sequences across players, concurrent sessions (from the action log). |
| M31.5 Design levers | M | Config options that remove the payoff: contract caps per verified person, rewards that can't be transferred, diminishing returns for repeated identical jobs. |

**Tests:** in the bot league, colluding alts are flagged on most seeds and honest players on
almost none (report the false-positive rate); every flag re-verifies.

### M32: elections and a campaign-finance register

**Where:** new `src/questless/politics/` (`elections.py`, `register.py`, `influence.py`),
`config.py` (`[politics]`), `player.py`, `app/` (Politics tab), M25 public pages.

| Task | Size | How |
|---|---|---|
| M32.1 Offices and powers | M | A `mayor` office with bounded powers from config (levy rate range, enforcement budget range). Decisions are evidence records like central-bank decisions. |
| M32.2 Elections | M | Every N days. Candidates are NPC guild leaders plus players who register. NPC votes follow a deterministic rule (which candidate's platform raises their income most, from a forecast fork), with ties broken by an `elections` RNG stream. Player votes are logged actions. |
| M32.3 Donations as transfers | S | `donate(campaign, amount)` (R5) moves coin to a `campaign:<id>` account with reason `donation`. Campaign spending (advertising raises NPC awareness) is a transfer to the town, so coin is conserved. |
| M32.4 The register | M | `register.build(world)` derives every entry from the ledger, never from a separate list, so it can't drift. Disclosure threshold, limits and the cooling-off rule come from config. |
| M32.5 Dark-money tracing | M | Follow coin backwards from a campaign account through intermediary accounts within K days (reuse M31.3's graph). Flag when an original source exceeds the limit; the flag is an evidence chain. |
| M32.6 Conflict-of-interest view | M | For each decision, compare each donor's income over 30 days with the counterfactual where the decision wasn't made (one forked replay). List donors who gained. |
| M32.7 Politics tab and wiki pages **(good first issue after M32.4)** | M | Register table, election results, a decision log with beneficiaries; public wiki pages per election. |

**Tests:** register totals == ledger donation transfers on every day; a limit breach through an
alt is flagged; an under-threshold donor's name never appears in the public vault (M25 leak test);
elections replay exactly.

**Pitfalls:** the counterfactual in M32.6 is a full replay; run it only when a decision is made
and cache it. Keep NPC voting simple and explainable; a voting rule nobody can explain defeats
the point of a transparency feature.

### M48: legitimacy and levy evasion

**Where:** new `src/questless/sim/legitimacy.py`, `sim/world.py` (`_collect_upkeep`,
`_pay_wages`, `TickStats`, `state_dict()`), `config.py` (`[legitimacy]`),
`contracts/provenance.py`, `contracts/causes.py`, `scenarios/legitimacy_spiral.toml`, `app/`.

**Design in one paragraph:** `World.legitimacy` is one number in [0, 1] for the town. Each day in
tick step 3, after `_pay_wages`, it moves under two pressures: the share of today's guard wages
left unpaid, and the share of NPCs hungry over the last few days. It falls fast and recovers
slowly (two rates in config). The levy runs before wages, so `_collect_upkeep` uses yesterday's
legitimacy: each NPC pays with a probability derived from it, and evaded coin stays in the NPC's
wallet. Nothing new touches the ledger, so conservation holds by construction.

| Task | Size | How |
|---|---|---|
| M48.1 Legitimacy stock | M | `legitimacy.update(world, stats)` called after `_pay_wages`. Inputs: `wages_unpaid / (wages_paid + wages_unpaid)` and the hungry share averaged over `hunger_window` days. The rates, window and starting value come from `[legitimacy]` (R1), with `enabled = false` in the baseline. Store it in `TickStats.legitimacy` and `state_dict()`. |
| M48.2 Levy evasion | M | In `_collect_upkeep`, an NPC pays with probability `compliance(legitimacy)` (a clamped linear map from config), drawn from `world.rng.stream("levy")` in sorted NPC order. Record `TickStats.levy_evaded`. No ledger change: the coin stays put. |
| M48.3 Evidence kinds **(good first issue after M48.1)** | S | `unpaid_wages`, `legitimacy_drop` and `levy_evasion`, each with a template and a `METRICS` key (R3). |
| M48.4 Causal walk | M | In `causes.py`, explain unpaid wages (and any town-funded guard contract) by walking back: unpaid wages ← levy evasion ← legitimacy drop ← earlier unpaid wages and hunger. The spiral is a loop, so stop at the first repeat of an evidence kind and link to its earlier occurrence. |
| M48.5 Scenario and chart | S | `scenarios/legitimacy_spiral.toml` extends the baseline with a small town treasury (R7); a legitimacy line on the town chart (R6). |

**Tests:** with `enabled = false` the baseline state hash is unchanged; with it on, conservation
holds every day and legitimacy stays in [0, 1]; a forced week of unpaid wages lowers it and a
funded month restores it; the spiral's chain re-verifies.

**Pitfalls:** the loop can lock a town into permanent collapse. That is a valid result for the
spiral scenario but not for the baseline, so test that a normally funded town recovers from a
one-week shock. Keep legitimacy one number per town here; per-site reach is M53's job.

### M49: beliefs and rumours

**Where:** new `src/questless/sim/beliefs.py`, `sim/behaviour.py`, `sim/market.py`,
`sim/guilds.py`, `contracts/needs.py`, `contracts/engine.py`, `contracts/provenance.py`,
`config.py` (`[beliefs]`), `scenarios/false_alarm.toml`.

**Design in one paragraph:** today every NPC decision reads `world.prices` or
`world.unit_price()` directly. M49 puts a view between the decision and the world:
`view(world, holder).price(good)`. A belief store keeps, per holder (an NPC or a guild) and good,
the believed price, whether the good is short, the day it was observed and the source. Holders at
the market observe the truth daily; holders at the mine and farms hear it only when a merchant who
was at the market reaches them, `delay_days` later. Guilds decide on contracts through their
beliefs, so a guild can fund a quest for a shortage that has already ended. With `delay_days = 0`
the view returns the truth and nothing changes.

| Task | Size | How |
|---|---|---|
| M49.1 Price view refactor **(good first issue)** | S | Route every decision-side price read in `behaviour.py`, `market.py` (buyer and seller decisions, not clearing) and `guilds.py` through `view(world, holder)`. The first view just returns the true price. Done when every test and the baseline state hash are unchanged. |
| M49.2 Belief store | M | `Belief(price, short, observed_tick, source)` per (holder, good), on `World` and in `state_dict()`. Updated after market clearing (step 5): market holders observe; merchants carry their beliefs to the sites they haul from, arriving `delay_days` later. Iterate in sorted id order. |
| M49.3 The board reads beliefs | M | `NeedTracker.update` and the candidate step in `contracts/engine.py` use the funder's beliefs about shortage and price, so a shortage a guild still believes in can produce a contract after it has ended. |
| M49.4 Belief evidence | S | A `belief` evidence kind: "the Blacksmiths Guild believed ore cost 31 (told by Elan Cart on day 40)". Its measure key reads the belief record, so `verify()` checks what was believed; the next step in the chain measures the truth. |
| M49.5 False-alarm scenario | S | `scenarios/false_alarm.toml`: a short mine shock and a long news delay, so a quest is posted after the mine has reopened (R7). |

**Tests:** with `delay_days = 0` the baseline hash is unchanged; no belief is ever dated after the
day it is used; the false-alarm scenario posts a stale quest on most seeds; every belief evidence
record re-verifies.

**Pitfalls:** the market must clear at true prices; only decisions use beliefs. One belief per NPC
per good is 400 entries a day, which is fine for one town; with M34 regions, keep beliefs at guild
level unless profiling says otherwise.

### M52: policy stress tests

**Where:** new `experiments/stress/` (`attackers.py`, `policy.py`, `run.py`), M23's workflow and
pull-request comment, M31.2's bot league.

**Design in one paragraph:** a policy is a TOML file that `extends` a scenario and changes only
knobs. An attacker is a function from what a player can see (the public board, prices and its own
wallet) to player actions, applied through `player.apply_action`, so every attempt is a replayable
save. The search runs seeds × attackers × (before, after) and scores each attacker's gain per day
against an honest reference player. A gain above a configured margin on most seeds is an exploit.

| Task | Size | How |
|---|---|---|
| M52.0 Exploit hunters **(can start now)** | M | Two or three scripted players over today's actions (claim and wait, buy before a scheduled shock, accept and abandon). Run them on the shipped scenarios and report coin gained per day against an honest player. They need nothing from M23 or M31. |
| M52.1 Policy overlays | S | Load a policy with `extends`; `policy.diff(a, b)` lists the knobs that changed. |
| M52.2 Attacker library | M | Port M31.2's bots (colluding alts, cornering) to the attacker interface; each documents its strategy in its docstring. |
| M52.3 Grid and scoring | M | Seeds × attackers × (before, after) through M23.2's `run_grid`. Default 5 seeds; the full grid is a nightly job. |
| M52.4 Findings report | S | For each exploit: the attacker, the seed, the saved replay and the ledger flows showing who lost. Posted in M23's pull-request comment. |
| M52.5 Planted-exploit test | S | A test policy with a deliberate hole (a contract that pays when nothing is delivered, like #43) must be found; the baseline must come back clean. |

**Pitfalls:** attackers must see only what a player sees, never world internals, or they will find
exploits no player could use. Keep each attacker small and explainable; a finding nobody can
explain can't be fixed.

### M56: unpaid guards turn bandit

**Where:** `sim/world.py` (`_pay_wages`, NPC state), `sim/shocks.py` (a `world` shock source),
`sim/transport.py` (theft), new `src/questless/sim/bandits.py`, `config.py` (`[bandits]`),
`contracts/provenance.py`, `contracts/causes.py`.

**Design in one paragraph:** each guard counts consecutive unpaid days. Past `desert_after` days
(rolled from a `desertion` RNG stream, in sorted guard order) the guard deserts: they stop drawing
wages and become a bandit. Every day the number of active bandits sets one `transport_capacity`
shock with `source = "world"` and a factor from config, and bandits take a share of the units
shipped through ordinary `theft` transfers. A bandit rejoins the guard roll when the town has paid
full wages for `return_after` days, or at once under an M57 amnesty.

| Task | Size | How |
|---|---|---|
| M56.1 Unpaid-day counter **(good first issue after M48.1)** | S | Count consecutive unpaid days per guard in `_pay_wages`; reset on a paid day. Store it on the NPC and in `state_dict()`. |
| M56.2 Desertion | M | Past `desert_after`, mark the guard as a bandit. Bandits draw no wages and are skipped by the guard-supply logic. Record `TickStats.deserted` and `TickStats.bandits`. |
| M56.3 World-sourced shock | M | Add `"world"` to `Shock.source`. Each day, replace the single bandit shock with one whose factor is `max(floor, 1 - per_bandit * bandits)`. Ending it is just a factor of 1. |
| M56.4 Theft | M | In `transport.ship`, after shipping, move `theft_share` of shipped units (by sorted owner, `alloc.split` for fair rounding) to bandit accounts with reason `theft`. Bandits eat and sell what they steal like any NPC. |
| M56.5 Evidence and walk | M | Evidence kinds `desertion` and `theft` (R3). In `causes.py`, when `_transport_shocks` finds a `world` shock, keep walking: shock ← desertions ← unpaid wages ← town treasury (M48's chain). |
| M56.6 Return | S | Bandits rejoin after `return_after` fully paid days or an amnesty (M57), with a `returned` evidence record. |

**Tests:** with `[bandits]` off, the bandits scenario and the baseline hash are unchanged; theft
keeps conservation; a guard unpaid for `desert_after` days deserts and returns after
`return_after` paid days; the transport chain reaches the treasury and re-verifies.

**Pitfalls:** this adds a second loop on top of M48's (bandits cut trade, trade funds the levy).
Check that a town with normal funding recovers after a one-week shock. Keep a floor on the
transport factor so a few bandits can't stop all trade.

### M57: amnesty and debt jubilee

**Where:** `finance/obligations.py` (M17), new `src/questless/politics/jubilee.py`, `config.py`
(`[jubilee]`), `sim/legitimacy.py` (M48), `sim/bandits.py` (M56), `contracts/provenance.py`,
`experiments/jubilee.py`.

**Design in one paragraph:** a jubilee is one recorded decision. It selects obligations from the
M17 registry by a rule from config, marks them `forgiven` and releases any collateral held in
escrow back to the debtor. No other coin moves: the creditor's claim is written off. Legitimacy
then rises by `boost × share of debtors relieved`. An amnesty is the same decision for people:
bandits (M56) and smugglers (M19) return to their old professions. The trigger is a town policy
rule (legitimacy below a threshold, with a cooldown) or, once M32 exists, a mayor's decision.

| Task | Size | How |
|---|---|---|
| M57.1 Forgiveness in the registry | S | `Obligation.forgive(tick, decision_id)`: status `forgiven`, collateral back to the debtor through the ledger, remaining principal and interest recorded as the creditor's write-off. |
| M57.2 Jubilee decision | M | `jubilee.declare(world, rule)` picks obligations by rule (`all`, `poverty`, `older_than`), forgives them in id order and records one decision with evidence listing each creditor's loss. |
| M57.3 Amnesty | S | `amnesty.declare(world)` returns bandits and smugglers to their professions, with `returned` evidence. |
| M57.4 Legitimacy and credit | S | Apply the legitimacy boost (M48). A config flag sets whether forgiven debts count as defaults in `credit.score` (M17.5). |
| M57.5 Trigger | S | A town policy rule from `[jubilee]`; later an M32 mayor decision through `player.apply_action`. |
| M57.6 Experiment | M | Paired seeds, with and without a jubilee: legitimacy, hunger and the loan rates offered afterwards. Report honestly, including when it backfires. |

**Tests:** the escrow invariant holds through a jubilee; the write-offs in the evidence equal the
registry's forgiven amounts; a jubilee replays exactly; an amnesty returns every bandit.

**Pitfalls:** a jubilee that fires every time legitimacy dips teaches lenders never to lend. Keep a
long cooldown and let the experiment show the trade-off rather than tuning it away.

### M33: theme packs and world topology

**Where:** new `themes/` folder, `config.py` (`[world]` graph, `theme`), `sim/entities.py`
(`Site` enum becomes data), `contracts/provenance.py` (templates per theme), `app/`.

| Task | Size | How |
|---|---|---|
| M33.1 Theme files | M | `themes/<name>.toml` with display names and flavour for every good, profession, place type, route type, shock and evidence kind. Loaded separately from the scenario so the same save can be shown in either skin. |
| M33.2 Rendering through the theme | M | Every user-facing string (chains, cards, charts, wiki) goes through `theme.name(kind, id)`. Evidence `TEMPLATES` move into the theme file with the current wording as the fantasy default. |
| M33.3 Places as a graph | L | Replace the fixed `Site` enum with `[[world.places]]` (id, type, position) and `[[world.routes]]` (from, to, travel days, capacity). Transport reads route capacity; the three current sites become a three-node graph in `baseline.toml`, so results don't change. |
| M33.4 Hardcoded-name test **(good first issue)** | S | A test that scans `src/questless/` for theme words ("caravan", "smith", "freighter") outside comments and fails if any appear in strings. |
| M33.5 Sci-fi scenario | S | `scenarios/scifi_reactor_failure.toml` extending the iron shortage with the sci-fi theme. |

**Tests:** identical state hash across skins; the baseline's numbers are unchanged by the graph
refactor (compare against stored v0.3 hashes).

**Pitfalls:** M33.3 touches a lot of code. Land it alone, behind passing tests, before anything
else in v0.4.

### M34: regions and simulation level of detail

**Where:** new `sim/regions.py`, `sim/lod.py`, `sim/transit.py`; `sim/world.py` (tick loop per
region), `sim/ledger.py` (pooled accounts), `persistence.py`.

| Task | Size | How |
|---|---|---|
| M34.1 Region model | L | `Region(id, places, npcs, market, prices, lod)`. The world holds regions; the tick loop runs each region's day in a fixed order (sorted ids), then delivers transit messages. |
| M34.2 Transit ledger | M | Generalise `IN_TRANSIT`: every shipment is a message `(from, to, assets, arrive_tick)` held on a transit account. Global conservation = regions + transit. |
| M34.3 Aggregate mode | L | Per region and profession group: total output from the group's capacity and inputs; consumption from population; one pooled account per group. Calibrate it so its daily aggregates match full mode's averages in the baseline. |
| M34.4 Switching levels | M | Full → aggregate: move every NPC's holdings into the group pool (ledger transfers). Aggregate → full: split back with `alloc.split` by each NPC's last known share. Totals are exact by construction. |
| M34.5 Dormant regions and fast-forward | M | Store the last tick; on wake-up, run the aggregate model for the missed days in one batch. |
| M34.6 Lazy generation | M | Region contents from `rng.stream(f"region:{id}")`, created on first contact, so the same seed always generates the same region regardless of visit order. |
| M34.7 LOD policy | S | Full if players or live contracts are present; aggregate if traded with in the last N days; else dormant. Config knobs. |
| M34.8 Benchmark | S | 1,000 regions, 10 active: time per day, recorded in `experiments/results/`. |

**Tests:** conservation every day; full → aggregate → full keeps totals; visit order doesn't
change a lazily generated region (generate A then B vs B then A); regional prices converge with
trade.

**Pitfalls:** RNG streams must be per region, or activating one region changes the random numbers
another region sees and breaks determinism.

### M35: a map shaped by the economy

**Where:** new `sim/growth.py`, `sim/population.py`; route and place data from M33; `app/` map.

| Task | Size | How |
|---|---|---|
| M35.1 Route usage | S | Exponential moving average of units shipped per route per day, in `TickStats` and `METRICS`. |
| M35.2 Road upgrades and decay | M | Above a usage threshold for N days, post a construction contract (R4) funded by the regions at each end; on fulfilment, capacity rises. Unused routes lose capacity slowly. |
| M35.3 New routes | M | If goods between A and C keep going via B and the detour costs more than a threshold, propose a direct route with a construction contract. |
| M35.4 Migration | M | Each week, a small share of NPCs whose wage is below the local cost of living move to the best reachable region (after travel time), through transit. |
| M35.5 Founding and abandonment | M | Region job surplus above a threshold founds a settlement at the nearest free place; population below a minimum marks the place as ruins (kept for seasonal worlds). |
| M35.6 Map export **(good first issue after M35.2)** | S | `questless map <save> --out map.json`: nodes, edges, sizes, histories, ready for a renderer. |

**Tests:** persistent price gap grows a road on every seed; a shocked single-industry region
loses population; every road and settlement has a verifiable chain.

### M36: ecology and the commons

**Where:** new `sim/ecology.py`; `config.py` (`[[resources]]`), `sim/behaviour.py` (harvest
decisions), M29 courts and M32 votes for rules.

| Task | Size | How |
|---|---|---|
| M36.1 Resource stocks | M | Per place: population `N`, growth rate `r`, capacity `K`, collapse floor. Daily regrowth `r·N·(1 − N/K)`, rounded with fractional carry like production. Stored as a ledger asset at the place, so harvests are transfers and regrowth is `produce`. |
| M36.2 Harvesting | M | Producers harvest from the stock instead of producing from nothing; output is capped by the stock. Open access: everyone harvests while it pays. |
| M36.3 Community rules | M | Charter clauses per resource: who may harvest, a quota, closed seasons. Enforced in the harvest step; violations recorded as evidence. |
| M36.4 Sanctions and disputes | S | Graduated fines from config; repeat offenders can be taken to court (M29). |
| M36.5 Rule changes by vote | S | Uses M32's voting; the vote's options are previewed with the M23 diff grid. |
| M36.6 Lesson | S | "The tragedy of the commons and how communities avoid it", for M26. |

**Tests:** open access collapses the stock on most seeds; a quota at the sustainable yield (`r·K/4`)
keeps it stable; conservation holds with regrowth counted as production.

### M37: legal automation, standing orders

**Where:** new `src/questless/automation/` (`lexer.py`, `parser.py`, `interpreter.py`,
`budget.py`); `player.py` (action budget); `app/` (rule editor).

| Task | Size | How |
|---|---|---|
| M37.1 Grammar | S | Write the grammar in `docs/STANDING_ORDERS.md` first: `when <condition>: <action>` lines, `and/or/not`, comparisons, a fixed set of functions (`price`, `stock`, `wallet`, `contract.open`), a fixed set of actions (the player ACTIONS), `limit N actions per day`. No loops, no variables, no user functions. |
| M37.2 Lexer and parser | M | Hand-written recursive descent producing a small AST of frozen dataclasses. Reject anything outside the grammar with a line and column. |
| M37.3 Interpreter | M | Evaluates conditions against a **public view** (M25) of the world plus the player's own holdings; each node evaluation costs one unit of fuel; out of fuel = stop for the day. |
| M37.4 Action budget for everyone | M | Every character has N actions a day in `player.apply_action`, whether from a person, a rule or an agent (M24). This is the anti-bot core. |
| M37.5 Tick slot and logging | S | Standing orders run once a day at a fixed slot, players in sorted order; each fired action is logged with `source: "rule:<n>"`. |
| M37.6 Rule editor **(good first issue after M37.2)** | M | A dashboard text area with live syntax errors and a "dry run" showing what would fire today. |
| M37.7 Bot-league comparison | M | The same strategy as an unlimited-speed scripted bot and as standing orders; show equal earnings. |

**Tests:** fuzz the parser with random input (it must never crash, only reject); hidden-state
functions don't exist in the grammar; budgets hold; replay is exact.

**Pitfalls:** never use Python's `eval`, `exec` or `ast.literal_eval` on rule text; the safety
comes from the grammar being tiny.

### M38: players post quests

**Where:** `player.py` (`post_contract`), `contracts/engine.py` (player requester), `contracts/model.py`.

| Task | Size | How |
|---|---|---|
| M38.1 Posting action | M | R5. Escrow first, then call the same `validation.py` checks used for NPC contracts. |
| M38.2 Stated vs verified evidence | S | A `stated_reason` evidence kind rendered as "Stated by the poster: ..." and never counted as verified. |
| M38.3 Fees and caps | S | Posting fee to the town; per-person live-contract cap from config. |
| M38.4 Alt detection hook | S | When an accepter shares ownership signals with the poster (M31.3), add a flag to the contract. |

**Tests:** the same need posted by an NPC and a player passes or fails validation identically;
reward can't exceed escrow; alt laundering is flagged.

### M39: treaties, sanctions and embargoes

**Where:** new `src/questless/diplomacy/` (`treaty.py`, `embargo.py`, `sanctions.py`); regions
(M34), courts (M29), elections (M32), smuggling (M19).

| Task | Size | How |
|---|---|---|
| M39.1 Governments per region | M | Each region has a government account and an office holder (M32). |
| M39.2 Treaties | L | Clause types: tariff rate, free passage, shared quota, arbitration. Both sides escrow a bond via the M17 registry. Clauses are enforced in transport and market steps. |
| M39.3 Embargoes | M | A blocked set of (route or region, goods). Transport refuses matching shipments; the resulting price gap feeds M19's smuggling trigger. |
| M39.4 Sanctions | M | A blocked set of accounts for transfers. Measure the cost to both sides with a counterfactual replay (cache it, as in M32.6). |
| M39.5 Arbitration | M | Treaty breaches are claims in M29's court between governments; awards paid from the bond. |
| M39.6 Diplomacy panel | M | Active treaties, embargoes and sanctions with their measured effects. |

**Tests:** an embargo creates smuggling on most seeds; a sanction's measured cost appears for both
sides; a breach pays from the bond; conservation and replay hold.

### M40: surrogate fast-forward experiment

**Where:** `experiments/surrogate/` (numpy as an `experiments` extra; never in the engine).

| Task | Size | How |
|---|---|---|
| M40.1 Dataset | M | Run many seeds and scenarios in aggregate mode; record (state aggregates today, flows tomorrow) pairs to CSV. |
| M40.2 Models | M | Start with linear regression; try a small gradient-boosted or neural model only if linear fails. Predict flows (production, consumption, trade), not balances. |
| M40.3 Evaluation | M | Error at 30, 90 and 365 days against the real aggregate model, with and without shocks. |
| M40.4 Safety net design | S | Predicted flows are applied through the ledger and clipped to what's available, so conservation holds whatever the model says. |
| M40.5 Write-up | S | `docs/SURROGATE.md`: where it works, where it fails, with numbers. |

### M41: docs, both skins and v0.4.0

Theme switch and multi-region map in the dashboard; README and BLUEPRINT updated with measured
results; changelog; tag v0.4.0.

### M53: the invisible border

**Where:** new `src/questless/geo/reach.py`, M34's regions, M48's levy statistics,
`contracts/engine.py` (patrol and collection contracts), `contracts/provenance.py`, `app/` (map
layer).

| Task | Size | How |
|---|---|---|
| M53.0 Per-site reach in one town **(can start after M48)** | S | Record levy owed, collected and evaded per site in `TickStats`; reach = collected ÷ owed. Works in today's single town. |
| M53.1 Reach index | M | Per site and town: levy reach, patrol days (guard days spent there) and the share of trade paying the market tax, combined with weights from config. Each component has a `METRICS` key so `verify()` can re-measure it. |
| M53.2 Border from reach | M | The town with the highest reach controls a site if it is above a threshold; otherwise the site is contested. Smooth over N days so borders don't flicker. |
| M53.3 Border evidence | S | A `border_shift` evidence kind: "the Mine passed from Ashford to contested on day 80: Ashford's reach fell from 0.7 to 0.3". |
| M53.4 Contested-zone quests | M | Patrol and collection contracts (R4) funded by a town that wants a contested site; the outcome is measured as reach gained. |
| M53.5 Map layer **(good first issue after M53.2)** | S | Colour sites by controlling town and hatch contested ones; a click shows the reach numbers. |

**Tests:** reach stays in [0, 1]; a two-town scenario with one town's wages cut moves the border on
most seeds; every `border_shift` re-verifies; replay gives the same borders.

**Pitfalls:** patrols need guards to have a location. If M34 doesn't give guards a site, use guard
wage-days assigned per region from config as a proxy and say so in the docs.

### M54: civilization DNA

**Where:** `config.py` (`mutate()`, `[founding]` bounds), M35's founding step, `sim/world.py`
(settlement lineage), M25 settlement pages, `report.py`.

| Task | Size | How |
|---|---|---|
| M54.1 `mutate()` **(can start now)** | M | `mutate(cfg, rng, bounds) -> ScenarioConfig` changes only the knobs listed in `[founding.bounds]`, each within its range, using a `founding` RNG stream. It returns a new config. Tests check bounds, determinism and that `to_dict()` round-trips. |
| M54.2 Lineage | S | Each settlement records `parent` and `mutations` (the knob diff), saved in `state_dict()`. |
| M54.3 Founding hook | M | When M35 founds a town, its config is `mutate(parent)`; colonists bring coin and goods from the parent through the transit ledger. |
| M54.4 Family tree | S | A wiki page and a report section: the tree of settlements, each with its diff from its parent. |
| M54.5 Selection report | M | Over a long run, which knob values are held by growing settlements and which by shrinking ones. |

**Tests:** mutated configs stay within bounds and pass the strict loader; the same seed gives the
same family tree; conservation holds across founding.

**Pitfalls:** mutating everything makes noise. Start with four to six institutional knobs (levy
rate, guard wage, relief policy, guild dues). Never mutate safeguards or conservation rules.

### M55: infrastructure dependency maps

**Where:** `contracts/causes.py`, new `src/questless/geo/dependencies.py`, M34's transit ledger,
M35's roads, `sim/shocks.py`, `app/` (dependency view).

| Task | Size | How |
|---|---|---|
| M55.0 Chain as a graph **(can start now)** | S | `causes.graph(world, contract)` returns the chain's evidence as nodes and its `caused_by` links as edges, as JSON. Useful today for M15's map and M25's wiki. |
| M55.1 Cross-region edges | M | When a region's input shortage traces to goods that stopped arriving, the walk continues into the sending region through the transit ledger's records. Bounded by depth and by the number of regions visited. |
| M55.2 Link failure shock | S | A shock kind that closes one route (a bridge or a road) for N days, with its own evidence. |
| M55.3 Dependency ranking | M | For a chosen site, fork the world once per nearby link, cut that link for 30 days and measure the site's loss (hungry NPC-days, output). Rank links by loss and cache the result per run. |
| M55.4 Maintenance quests | M | The top-ranked links attract funded maintenance contracts (R4); the evidence cites the loss from the forked replay. |
| M55.5 Dependency view | S | A ranked list and a map overlay of the critical links for the selected site. |

**Tests:** a three-region bridge cut gives a chain crossing at least two regions that re-verifies
at every step; the top-ranked link matches the largest forked-replay loss; the graph export
round-trips through JSON.

**Pitfalls:** ranking forks the world once per link. Limit it to links within K hops and run it on
demand or weekly, never every tick.

### M58: fairness for late joiners

**Where:** `metrics.py` (concentration and mobility), `sim/world.py` (`_collect_upkeep`),
`config.py` (`[fairness]`), new `src/questless/fairness/` (`claims_tax.py`, `dividend.py`,
`grants.py`), `contracts/engine.py` (apprentice contracts), M31's bot league,
`experiments/late_joiners.py`. Evidence and references:
[RESEARCH.md](RESEARCH.md#m58-fairness-for-late-joiners).

**Design in one paragraph:** the experiment harness runs identical bot strategies that join at
different days and compares them at equal time played. The report breaks the gap down by channel
(reputation, capital, land, power, information), so a designer can see which lever targets which
cause. Every lever is a knob in `[fairness]`, off in the baseline, and every coin it moves is an
ordinary ledger transfer with its own reason (`levy`, `claims tax`, `dividend`, `grant`).

| Task | Size | How |
|---|---|---|
| M58.1 Concentration metrics **(good first issue, can start now)** | S | Gini coefficient and top-10% share of coin (and later of land) per day in `metrics.py`, charted on the economy tab. |
| M58.2 Late-joiner harness **(can start now)** | M | Run the scripted player from `experiments/shock_vs_baseline.py` joining on day 0 in one run and day 1,000 in another; compare income, contracts claimed and wealth at equal days played. Multi-player comparison in one world follows once M31 lands. |
| M58.3 Levy brackets **(can start now)** | S | Turn the flat `upkeep_rate` into `[[town.levy_brackets]]` (threshold, rate). The baseline keeps one bracket, so its state hash is unchanged. No exemptions and no cap by design. |
| M58.4 Gap report | M | Per run: income gap at equal tenure, time to first worthwhile contract, board access share, mobility (rank correlation of wealth year to year), r − g by asset type, and the gap split by channel. |
| M58.5 Claims tax and dividend | M | Tax each claim on its unworked potential output (measurable from site config); pay mine royalties into a fund that pays every character equally. Both are evidence records with measure keys. |
| M58.6 Entry and start levers | M | Guild entry fees and quotas, apprentice contracts (R4) reserved for low-tenure players, and a starting grant graded by family wealth (once dynasties exist). |
| M58.7 Lever reports with evidence | S | Each lever's section in the report quotes its research finding from RESEARCH.md and its "what the model leaves out" note. |

**Tests:** with every lever off the baseline hash is unchanged; levy brackets, claims tax, dividend
and grants all conserve coin; the gap report re-verifies from `TickStats`; an attacker that funnels
newcomer rewards to a main through alts is caught (M52, M31).

**Pitfalls:** apprentice lanes and starting grants are exactly what alts farm, so don't enable them
before M31's one-person-one-character safeguards. Don't tune the levers until veterans' rewards
collapse: the second acceptance bound exists to stop that. Keep each lever's effect separately
measurable; turning on five at once makes the report unreadable.

### M42: privacy as code

**Where:** new `privacy/` folder (`data_inventory.toml`, `DPIA_TEMPLATE.md` in `docs/`),
`src/questless/identity/` (separate store), `wiki/visibility.py` roles, `audit.py` access log.

| Task | Size | How |
|---|---|---|
| M42.1 Data inventory | S | One entry per personal field: name, purpose, lawful basis, retention days, tier. |
| M42.2 Inventory test **(good first issue)** | S | Walk the player and identity dataclasses with `dataclasses.fields`; fail on any field missing from the inventory. |
| M42.3 Identity store | M | Random player ids in the world; a separate store maps them to account data, encrypted per player. The engine stays stdlib, so the demo uses a pluggable cipher interface with a test implementation; production uses a real library outside the engine. |
| M42.4 Crypto-shredding demo | S | `questless erase <player>` deletes the key and mapping; a test shows the world hash chain still verifies and no personal field is readable. |
| M42.5 Access log into M30 | S | Every dev-tier read appends a record (role, reason, page) to the tamper-evident log. |
| M42.6 Retention job | S | Deletes integrity signals older than their retention unless a case is open; tested with a fake clock (the engine's tick, not wall time). |
| M42.7 DPIA template | S | A Markdown template with the questions a data protection impact assessment needs, filled in for M31 as the example. |

### M43: language bridge

**Where:** `themes/` (per-language strings and glossaries), new `src/questless/language/`
(`messages.py`, `graded.py`, `adapter.py`), `app/`.

| Task | Size | How |
|---|---|---|
| M43.1 Strings per language | M | Move every user-facing string and evidence template into `themes/<theme>/<lang>.toml`; English and Spanish first. A test checks every key exists in every language. |
| M43.2 Message format | S | `Message(channel, author, lang, text, translations={})`; global channels default to `en`. |
| M43.3 Translation adapter | S | An interface with a no-op implementation and a dictionary-based test one; real machine translation plugs in outside the engine. |
| M43.4 Graded texts | M | Each quest and NPC template gets an optional `plain` variant; a readability check (sentence length, word frequency list) in tests. |
| M43.5 Glossary highlights **(good first issue)** | S | Theme glossary terms marked in rendered text with their definition. |
| M43.6 Learning mode | M | A per-player setting (player tier) that controls translations, graded texts and the private vocabulary record. |

**Pitfalls:** never translate structured contract fields through the adapter; render them from
data in each language so they can't drift.

### M44: steward NPCs

**Where:** new `src/questless/stewards/` (`health.py`, `roles.py`, `policy.py`), the bot league
(M31.2), `experiments/stewards.py`.

| Task | Size | How |
|---|---|---|
| M44.1 World-health metrics | M | Share of players in groups, sessions since a player's last interaction with a human, new players' first successful contract, Gini coefficient of wealth, market liquidity, tension. In `TickStats` and `METRICS`. |
| M44.2 Simulated players with social behaviour | M | Extend the bot league: players join groups when offered complementary contracts, drift away after long stretches without success. Simple, documented rules. |
| M44.3 Roles as controllers | L | Mentor, matchmaker, understudy, rival, caretaker: each a deterministic controller with its own account, action budget and trigger conditions from config. |
| M44.4 Group contracts | M | A contract kind (R4) with several role slots (e.g. haul + guard + craft); rewards split by slot; bonus for mixed new/veteran groups. |
| M44.5 Intervention evidence | S | Every steward action records why (which health metric, which threshold). |
| M44.6 Trained policies (stretch) | L | Train a steward policy in the M24 environment against the health metrics; freeze it and load it as data. |
| M44.7 Experiment | M | Stewards on/off over paired seeds: grouping, inequality, new-player success. Report honestly. |

**Pitfalls:** a caretaker that trades too well crowds out players. Cap its volume and its price
advantage, and measure human trade with it on and off.

### M45: skills passport

**Where:** new `src/questless/skills/` (`detectors.py`, `passport.py`), M25 player vault, M26
lessons.

| Task | Size | How |
|---|---|---|
| M45.1 Detector format | S | A detector is a pure function over a player's verified actions and their evidence, returning a skill id and the evidence, or nothing. |
| M45.2 First ten detectors | M | One per major skill in SKILLS.md; each a good first issue once M45.1 exists. |
| M45.3 Passport page | S | Player-tier wiki page listing skills with evidence links and lesson links. |
| M45.4 Signed export | M | A JSON credential signed with an Ed25519 key in production; the engine defines the format and uses HMAC (stdlib) for tests. Marked non-transferable. |
| M45.5 Teacher view | S | Aggregates over consenting students only, with the 5-contributor rule from M25. |

### M50: told history versus the log

**Where:** new `src/questless/history/` (`claims.py`, `retelling.py`, `legends.py`), M49's belief
network, `player.py` (`fact_check`), `config.py` (`[history]`), M25 wiki pages.

**Design in one paragraph:** a claim is always derived from one real evidence record, so it can be
wrong but never invented. When an NPC is affected by an event (it went hungry, its guild funded a
contract), it starts a claim with the measured value. Claims spread along the same network as M49's
beliefs, and each retelling applies a fixed distortion rule for that kind of event. Players check
claims against `measure()`. Claims that are retold often enough become legends with a wiki page and
a verdict.

| Task | Size | How |
|---|---|---|
| M50.1 Claim record | M | `Claim(id, event_ref, teller, stated_value, told_tick, retellings)`, on `World` and in `state_dict()`. `event_ref` points to a real evidence record; `stated_value` starts as its measured value. |
| M50.2 Retelling rules | M | Per evidence kind, a distortion from config (losses grow by a factor, credit shifts to the teller's guild), drawn from a `retelling` RNG stream. Rules never change `event_ref`. |
| M50.3 Spreading | S | Claims travel along M49's network: with merchants between sites and within guilds. |
| M50.4 `fact_check` action | S | `fact_check(claim_id)` (R5) compares `stated_value` with `measure(event_ref)`; a correction pays a small town-funded reward and marks the claim. |
| M50.5 Legends | M | A claim retold more than N times becomes a named legend with a wiki page (M25): the told version, the measured version and a verdict (true within 10%, partly true or false). |
| M50.6 Narration adapter (optional) | S | An interface that phrases a claim in prose, with a template-based test implementation. The adapter receives the numbers and returns text; it can't change either. |

**Tests:** every claim's `event_ref` is a real evidence id; retelling never changes the event; a
fact check recovers the measured value; replay produces the same legends.

**Pitfalls:** claims multiply fast. Cap claims per event and drop the least-retold ones first.

### M51: records that decay

**Where:** new `src/questless/history/archive.py`, `config.py` (`[archive]`), M33 theme strings,
`contracts/` (a RECOVER kind, R4), M25 wiki, M30 audit.

| Task | Size | How |
|---|---|---|
| M51.1 Archive records | S | One record per notable event (shocks, posted contracts, M50 legends) with a `condition` in [0, 1]. Records are information, not goods, so they are not ledger assets. |
| M51.2 Decay and upkeep | M | Condition falls daily by a config rate. An institution account, funded by the town or a guild through ordinary transfers (reason `archive upkeep`), restores condition up to its budget, oldest-used records last. |
| M51.3 Loss | S | At condition 0 a record is lost; its wiki page keeps only the told history (M50) with a "record lost on day N" note. |
| M51.4 RECOVER contracts | M | A contract kind (R4) to recover a lost record from a site (ruins, an abandoned town, another region); fulfilment restores it at partial condition. The evidence cites the loss. |
| M51.5 Institution names **(good first issue)** | S | Theme-pack strings (M33): library, scholars, academy or college in fantasy; a data vault or archive in sci-fi. |

**Tests:** an unfunded archive loses records in the documented order; a recovery restores one; the
M30 audit verifies the developer log across every loss.

**Pitfalls:** in-world loss must never touch the engine's own journal or the evidence `verify()`
reads. The archive is a separate, in-world copy.

### M46: docs and v0.5.0

Update PRIVACY_AND_IDENTITY, SKILLS and BLUEPRINT with what was built; changelog; tag v0.5.0.

---

## Part 5: backlog ideas, sketched

Not scheduled. Each line says what it builds on and the core of how. If you want to take one,
open an issue with a short design first.

### Economy and quests

| Idea | Builds on | How (sketch) |
|---|---|---|
| Shock insurance | M17, M20 | Policies are obligations; premiums priced from forked forecasts; payouts triggered by verified `shock` evidence, so claims can't be faked. |
| Shortage forecasts | Determinism | Fork the world N times with different `forecast` RNG streams, step 30 days, report the share of forks with a shortage. |
| Crowdfunded repairs | R4 | A contract kind whose fulfilment ends a shock early; funded by many small pledges held in escrow and refunded if the target isn't met. |
| Drone fleets | M17 | Player-owned capital that adds transport capacity; merchants lose hauling income, which the chain shows. |
| Strikes and unions | M17, M19 | NPCs coordinate when wages fall below food cost; a strike sets their output to zero until a negotiated wage contract is funded. |
| A profit-maximising NPC corporation | M18 | One agent with a greedy policy that buys up stock to raise prices; anti-cornering rules become a designer knob. |
| NPC memory and favours | M29 | Per-NPC ledger of help received; rewards and prices adjust; courts cite it. |
| Reverse auctions for contracts | M31.1 | Many players bid the lowest reward they'll accept; seeded tie-breaks keep it deterministic. |
| Labour mobility | Behaviour | Broke NPCs switch to the most profitable profession after a retraining delay; a config cap prevents stampedes. |
| Bot league | M31.2 | Already part of M31. |
| Sabotage traced to the saboteur | M19 | A sabotage action creates a shock with a hidden cause; detective quests (fog of cause) reveal it. |
| Research grants | R1 | Persistent shortages unlock a funded research contract that adds a new recipe to the config at runtime (logged). |
| Elected mayor | M20, M29 | Guild members vote each season; the winner sets the levy within bounds. |
| Seasons and climate | Shocks | Periodic modifiers on farm output from config. |
| Rumours and imperfect information | M49 | Now M49, beliefs and rumours. |
| Births, bankruptcy and succession | M17 | Bankrupt NPCs sell assets; new NPCs arrive when the town prospers. |
| Contract feed for companion apps | M25 | A public-tier JSON feed of open contracts; a webhook per new contract. |
| Fog of cause | M25 | Chain steps carry a visibility tier per player; investigation actions reveal them. |
| Impact ledger | M24.1 | The impact score shown per player. |
| Drama director | Shocks | A controller that picks shocks to keep a tension metric (share of NPCs in need) within a target band. |
| NPC startups | Research grants | Idle NPCs pitch a business (new recipe + profession); players fund it like a loan with equity. |
| Consequence mirror | M24.1 | Show the no-player replay side by side. |
| Escalation ladders | R4 | Unmet needs escalate through unrest, strike and migration stages, each a contract kind. |
| Item biographies | Ledger | Goods become lots with ids for crafted items; the lot carries its production chain. Expensive; prototype on tools only. |
| Depletion and prospecting | Shocks | Mine capacity decays; a prospecting contract adds a new site. |
| Morale | Behaviour | A morale stat that multiplies output; festivals are food and ale contracts that raise it. |
| Shard diplomacy (superseded by M34) | Persistence | Export a caravan file from one run and import it as outside stock in another, with both hashes recorded. |

### 2030s differentiators

| Idea | Builds on | How (sketch) |
|---|---|---|
| Daily Crisis | M24.1, M28 | Seed = date; shock picked by the drama director; score = impact; leaderboard of save files anyone can replay. |
| Open Quest Protocol | Provenance | JSON Schema for contract, evidence and outcome; `questless export --oqp`; a validator; tiny Godot and web clients that render a chain. |
| Audience-driven world | M28 | Votes are logged actions from a `audience` account, so streamed worlds replay exactly. |
| Instant localization | Templates | Move `TEMPLATES` into per-language files; a test asserts every evidence kind has every language. |
| Asynchronous companion play | Contract feed | Accept and deliver over an HTTP API (FastAPI in `app/`, not the engine). |
| Real-money-trading detection | M31.3 | The transfer-graph signals, tuned for value moving to one account. |
| Provably fair world | M30.3 | Commit-reveal for every scheduled shock and daily seed. |
| Referendum preview | M23 | Each policy option is a config override; run the diff grid; publish the predicted effects before the vote. |
| Constitution file | M29 | Rules live in a versioned TOML; amendments are votes; the diff is the public record. |
| Prediction markets | M18, M30 | Binary contracts on metrics; settled by `measure()` on the resolution day. |
| Inflation-indexed loot | M20 | Rewards scale with the CPI. |
| Pollution and Pigouvian taxes | R3, M20 | Forge output reduces nearby farm output; a tax lever and a filter contract. |
| Historical shock packs | R7, M26 | Scenario files with lessons comparing outcomes with history. |
| Scenario marketplace | M23 | Each published scenario carries its diff-grid badge. |

### Society, law and money

| Idea | Builds on | How (sketch) |
|---|---|---|
| Freedom-of-information requests | M25, M29 | A request action names a dev-tier fact; after N days a rule table decides release or exemption; released facts move to the public view with the request as provenance. |
| Corrupt treasurers and audit quests | M17, M29 | A seeded chance that a treasurer moves coin to a private account with a misleading `reason`; an audit contract compares reported vs ledger balances and files a claim. |
| Player journalism with fact checks | M25, R3 | Articles are Markdown with inline `{{measure: price, tools @ 74}}` tags; publishing evaluates each tag with `measure()` and adds a badge. |
| Guild banks and bank runs | M17, M20 | Deposits are obligations owed by the guild; a reserve ratio knob; withdrawals beyond reserves default unless the discount window lends. |
| Land registry and mining claims | M17, M29 | Titles as records owned by accounts; mortgages via the obligation registry; compulsory purchase pays a valuation from recent output. |
| Price-control votes | M19 | A vote action sets a temporary ceiling below the clearing price; rationing and smuggling then follow from existing mechanics. |
| UBI vs targeted relief | M17, M20 | A config switch for a daily flat transfer from the town (or minted); a new experiment arm in M22's runner. |
| Million-agent load harness | M31 | Bot league with thousands of players; profile with `cProfile`; report time per day by subsystem. |
| Reading-level selector | M16 | Three renderers over the same chain: `summarise`, `render`, and an expert view showing measure keys and values. |

### Massive-scale 2030s ideas

| Idea | Builds on | How (sketch) |
|---|---|---|
| Dynasties | M17, M32 | An `age` on NPCs and characters; death transfers holdings by will or default rules, with an inheritance tax to the town; the player takes over an heir. |
| Seasonal worlds on ruins | Persistence, M25, item biographies | At season end, export the wiki and chosen items; the next scenario's `extends` loads them as buried artifacts at sites, found by excavation contracts. |
| A map shaped by the economy (now M35) | Transport | Roads gain capacity where shipped volume stays high and decay where it doesn't; new sites open when a site's output and population pass thresholds. |
| Ecology (now M36) | R1, R6 | A logistic-growth population per resource site; harvesting draws it down; communal rules (quotas, seasons) are config or charter clauses. |
| Legal automation (now M37) | R5, M31 | A tiny rule language parsed into a safe AST (no Python `eval`); rules run in a fixed tick slot with per-character action limits; fired rules are logged actions. |
| Executable guild charters | M29, M32 | Charter clauses as typed records (dues rate, payout rule, quorum); the engine checks treasury spends against them; amendments are votes. |
| Players post quests (now M38) | R4, M31.1 | A `post_contract` action for players, going through the same validation as NPC contracts; provenance cites the player's stated need and their stock. |
| Treaties, sanctions and embargoes (now M39) | M17, M19, multi-settlement | Treaties are obligations with bonds; an embargo blocks transfers between named accounts; smuggling triggers already respond to the gap. |
| Migration between regions | M34, M35 | Player and NPC moves are transit messages between regions; regions publish tax and service levels that the migration rule compares. |
| World-scale public goods | Crowdfunded repairs | A pledge contract with a target and deadline; a shock fires if it fails; contributions are public. |
| Transparent experiments | M23, M25 | Experiment specs are config overrides published in the wiki; a vote action approves them; results come from the M23 diff grid. |
| Paid mentors | M24.1 | A mentorship contract escrowed by the mentee or a guild; payout scales with the mentee's impact score after 30 days. |
