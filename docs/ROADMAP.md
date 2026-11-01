# Roadmap: v0.2 to v0.6 build path

Status: **planned, not started** · drafted 2026-10-21 · follows v0.1.0 and [REVIEW.md](REVIEW.md)

v0.2 turns the prototype into a richer economy:
- **Fixes and usability:** the bugs and UX problems found in the review.
- **Relief and loans:** an answer to poverty traps.
- **Futures:** a financial layer for players who would rather trade than fight.
- **Smuggling:** a lawful/unlawful layer.
- **Central bank:** monetary policy that fights inflation and deflation in the open.
- **Run reports:** an exportable record of each run.

Every new mechanic keeps the v0.1 guarantees:
- coin and goods are conserved (from M20, coin supply changes only through recorded mint and
  burn operations);
- every obligation is escrowed before it exists;
- every contract or trade carries provenance;
- runs are deterministic and replayable;
- invariants are checked on every simulated day.

## Build order

| # | Milestone | Depends on | Estimate |
|---|---|---|---|
| M13 | Bug fixes (REVIEW B1, B2, B7) | none | 0.75 h |
| M14 | Readable charts and compact layout | M13 | 2 h |
| M15 | Clickable evidence and map highlight | M14 | 1.5 h |
| M16 | Quest summaries, profit and "Why no quests?" | M14 | 1 h |
| M17 | Relief and loan quests, credit scores | M13 | 4 h |
| M18 | **Futures contracts on goods** | M17 (obligation registry) | 8 h |
| M19 | **Smuggling and black markets** | M13 | 7 h |
| M20 | **Central bank and monetary policy** | M17 (policy rate), M18 (forward prices) | 8 h |
| M21 | Exportable run report | M17-M20 | 1.5 h |
| M22 | Re-run experiments; update docs and media | all | 2.5 h |

- **Total:** about 36.5 h, roughly 4.5 working days. Past milestones ran about 1.3× over
  estimate, so plan for **6 days**.
- **Critical path:** M13 → M17 → M18 → M20 → M21 → M22.
- **Parallel work:** M14-M16 (UI) and M19 (smuggling) don't depend on each other.
- **Cut order if behind:**
  1. the futures UI (keep the engine and tests);
  2. smuggling's player run contracts (keep NPC smugglers and enforcement);
  3. map flows in M15;
  4. the central bank's discount window (keep the rule-based mint and burn).

## M13: bug fixes (0.75 h)

- **Fixes:**
  - Reject non-finite numbers (`nan`, `inf`) in `config._number` and `player.shock`.
  - Record guild treasuries after contracts run, and report escrowed coin separately.
  - Make `step(days < 0)` raise `ValueError`, and give unknown ids clear errors.
- **Accept when:** a NaN or infinite shock raises `ActionError` and leaves state unchanged; a
  TOML file with `factor = nan` raises `ConfigError`; the treasury card equals the chart's last
  point.

## M14: readable charts and compact layout (2 h)

- **Charts:**
  - Production and prices as **% of normal**, with one small chart per good as an option.
  - A grey warm-up band for days 0-9.
  - Unmet demand as **% of demand**.
  - Neutral hatch for shock windows, with labels above the plot.
  - Distinct hue set for guilds.
  - Zero-based axes, and escrowed coin shown as a lighter band in the treasury chart.
- **Layout:** one compact sticky bar (brand, day, time controls, shocks). The intro text moves
  into "How it works".
- **Accept when:** at 1280 px the controls fit on one row and the first quest's chain is visible
  without scrolling, and every economy chart can be read for all four goods.

## M15: clickable evidence and map highlight (1.5 h)

- **Evidence:** each measured step in the chain is clickable. The evidence chart then plots
  that metric with its baseline and threshold, read from its `measure` key.
- **Map:**
  - The selected quest's requester and beneficiaries are ringed on the map.
  - The shocked site pulses.
  - Road thickness shows units shipped today, and each site gets a stockpile gauge.
- **Accept when:** clicking each chain step in the Iron Shortage quest shows a chart whose last
  value equals the number in that step.

## M16: quest summaries, profit and "Why no quests?" (1 h)

- **Summary:** a one-sentence plain-language summary above the chain, generated from the
  evidence.
- **Quest cards:** estimated profit (reward minus the cheapest sourcing route) and a days-left
  bar.
- **Wording:** "Guild order", "Transport job", "Town order".
- **Empty board:** a "Why no quests?" panel listing suppressed needs by reason, plus today's
  poverty counts.
- **Accept when:** Mine Disaster at day 149 explains its empty board with poverty numbers.

## M17: relief and loan quests, credit scores (4 h)

- **Engine:**
  - A new `finance/` package with an **obligation registry**: who owes what to whom, and when.
    It's backed by ledger accounts, so conservation still holds.
  - **Relief contract:** the town or a guild funds working capital for poverty-trapped NPCs;
    the player delivers coin or tools.
  - **Loan contract:** the player lends to an NPC or guild with an interest rate and a
    repayment schedule.
  - **Credit score** per borrower from repayment history. Defaults are recorded with their
    provenance.
- **Provenance:** a new evidence kind, `poverty`, recording unaffordable demand against income.
- **Accept when:** in the Mine Disaster experiment with a scripted lender, at least 5 of 10 seeds
  recover (0-2 of 10 today); conservation holds; and defaults and repayments replay exactly.

## M18: futures contracts on goods (8 h)

Players and guilds lock in a price today for delivery later. Smiths hedge against ore spikes;
speculators profit by predicting shocks.

- **Instrument:** `Future(good, qty, strike, delivery_tick, buyer, seller)`, physically settled.
  - **Buyer** escrows `qty × strike` in full on opening.
  - **Seller** posts collateral of 30% of notional.
  - **At delivery,** the seller's goods go to the buyer and the escrow goes to the seller.
  - **If the seller can't deliver,** the buyer gets their escrow back plus
    `max(spot - strike, 0) × qty` out of the collateral; any shortfall is recorded as a default
    against the seller's credit score (from M17).
- **Market maker:** the Merchants Guild quotes forward prices for 10, 20 and 30 days:
  `forward = spot × (1 + carry × days) × risk factor from stock cover`. Its open exposure is
  capped by its treasury.
- **NPC hedgers:**
  - Smiths buy ore futures when their ore cover is below `stock_days` and the price is
    rising.
  - Miners sell futures when the price is above base, locking in income.
  - Both are bounded by budget and exposure rules.
- **Player actions:** `buy_future`, `sell_future` and `close_position` (offset at the current
  quote), all logged and replayable.
- **Provenance:** each quote records its inputs (spot, cover, carry), and each settlement records
  spot vs strike.
- **Dashboard:** a Futures tab with a quote board, open positions, mark-to-market profit and loss,
  and a settlement history.
- **Accept when:**
  - Conservation holds, and escrow equals open notional plus collateral on every day.
  - Settlement and default paths are covered by tests.
  - A determinism test passes with futures open across save and load.
  - In the iron shortage, smiths who hedged before the shock have fewer idle days than those
    who didn't (paired seeds).

## M19: smuggling and black markets (7 h)

When prices hit their ceiling or bandits cut the roads, smugglers sell at a premium. The town
posts enforcement contracts while smugglers post run contracts. Players choose a side, and their
reputation with the town and the guilds shifts.

- **Smugglers:** a smuggler faction (its own account and reputation) appears when either
  condition holds for 3 or more days:
  - the price is at its ceiling;
  - a transport shock is active and the site backlog exceeds the threshold.
- **Contraband trade:** contraband comes from `outside` stock at 1.5× the market price. It
  bypasses market tax and transport capacity, and is sold to NPCs with unfilled demand. The
  premium goes to the smugglers' account; it isn't created from nothing.
- **Enforcement and lawlessness:**
  - Enforcement strength depends on guard numbers and town funding.
  - Each shipment is intercepted with a seeded probability; confiscated goods go to the town's
    stock, which the town sells at market later.
  - A **lawlessness** index rises with smuggled volume and lost tax.
- **Contracts:**
  - **Enforcement (town-funded):** intercept a smuggling run. The bounty is paid from escrow;
    town and Merchants Guild reputation go up, smuggler reputation goes down.
  - **Run (smuggler-funded):** carry contraband past the guards. A higher reward with an
    interception risk; if caught, the goods are confiscated and town reputation falls.
  - Smiths and farmers who got cheap goods during a shortage may *like* smugglers. Reputation
    effects differ by guild, so choosing a side has real trade-offs.
- **Provenance:** smuggler appearance cites the price-at-ceiling or transport-shock evidence, and
  enforcement contracts cite lost tax and lawlessness.
- **Dashboard:** smuggling routes as dashed lines on the map, an "Illicit" badge on run
  contracts, the lawlessness gauge, and town and smuggler reputation.
- **Accept when:**
  - The baseline has no smuggling across 10 seeds.
  - Bandits and a drought produce smuggling within 7 days.
  - More enforcement means less smuggled volume (paired seeds).
  - Conservation and determinism hold, and reputation changes match each side's actions.

## M20: central bank and monetary policy (8 h)

The town gets a central bank that expands or shrinks the coin supply to fight inflation or
deflation, with every change recorded and explained. This deliberately relaxes the fixed-coin
rule, so the engine has to make the relaxation *auditable*.

- **Ledger:**
  - New `mint` and `burn` operations, allowed only for the `central_bank` account.
  - Conservation becomes: `total coin == genesis + minted - burned`, checked every day.
  - Every mint or burn is journalled with its reason and policy evidence.
- **Price index:** a consumer price index (CPI) from the economy's actual consumption basket at
  base prices, plus a 30-day inflation rate. Both are recorded in `TickStats` and measurable by
  `verify()`.
- **Policy rule** (Taylor-style, deterministic, bounded), deciding each day:
  - **Deflation, or many NPCs too broke to work** → **expand**:
    - mint into the town treasury (funding wages and relief);
    - cut the policy rate.
  - **Inflation above band** → **contract**:
    - burn a share of town tax and upkeep receipts;
    - raise the policy rate.
  - Daily mint and burn are capped at a configured share of the money supply (for example,
    0.5%), so the bank can't run away.
- **Policy rate feeds the rest of the economy:**
  - loan interest (M17);
  - the futures carry cost (M18);
  - guild relief generosity.
- **Discount window:** a guild can borrow from the bank in an emergency at the policy rate plus a
  penalty, which may let a guild fund an emergency contract it can't afford today.
- **Provenance:** a new evidence kind, `monetary_policy` (for example, "CPI fell 6% in 30 days;
  bank minted 120 coin into the town treasury; rate cut to 2%"). It appears in the chains of
  any contract the policy affected.
- **Config:** `[central_bank]` with `enabled`, the CPI target and band, mint and burn caps, rate
  bounds and penalty. Off by default in `baseline.toml` (so v0.1 results stay comparable); on in a
  new `monetary.toml` scenario.
- **Dashboard:**
  - A "Central bank" panel with CPI against the target band, money supply and the policy rate.
  - A log of policy decisions with their reasons.
  - A player action to **lobby**: spend reputation with a guild to push for easing or
    tightening, recorded like any action.
- **Accept when:**
  - The new conservation identity holds every day, and replay is exact with the bank on.
  - The 2,000-day baseline with the bank on keeps tools and weapons prices within ±25% of base
    (fixing REVIEW B5's drift).
  - The mint and burn caps hold under extreme shocks.
  - Mine Disaster with the bank on recovers on more seeds than with it off (paired seeds), or
    the result is documented if it doesn't.
  - Every mint and burn in a run re-verifies against the recorded CPI.

## M21: exportable run report (1.5 h)

- **CLI:** `questless report <scenario|save> --out report.html` (or `.md`).
- **Dashboard:** a "Download report" button.
- **Contents:**
  - the scenario and its shocks;
  - headline indicators;
  - every contract with its rendered chain and verification status;
  - outcomes of delivered contracts;
  - loans, futures, smuggling and monetary-policy summaries;
  - the economy charts.
- **Format:** self-contained, with charts as inline SVG.
- **Accept when:** a report for each scenario opens offline and every chain in it re-verifies.

## M22: experiments and docs refresh (2.5 h)

- **New experiment arms:** relief and loans on/off, NPC hedging on/off, enforcement low/high,
  central bank on/off.
- **Doc updates:** RESULTS.md, README (results table and screenshots), SIMULATION_SPEC.md and the
  changelog; tag v0.2.0.
- **Accept when:** the experiments regenerate from one command, and the docs quote only
  generated numbers.

## v0.3 scope: studio, research and teaching tools

Status: **in scope, planned after v0.2** · added 2026-10-21

v0.2 makes the economy richer. v0.3 makes it useful to three audiences beyond the demo:
- **Studios:** balance changes reviewed like code (M23).
- **AI researchers:** a benchmark for agents that must reason about causes (M24).
- **Players and teachers:** a world that documents itself (M25) and teaches real economics and
  politics from what actually happened in it (M26).

Five milestones added from the
[#53 idea bank](https://github.com/Adiezc/questless/issues/53) (2026-10-23) give M32's politics
real feedback and let studios attack a policy before it ships: legitimacy (M48), beliefs and
rumours (M49), policy stress tests (M52), unpaid guards turning bandit (M56) and amnesty and debt
jubilee (M57). A sixth, respectful play (M59), adds a check that no change makes the game
punish players for having a life.

The v0.1 and v0.2 guarantees still apply. New dependencies stay optional extras; the engine stays
standard-library only.

### Build order

| # | Milestone | Depends on | Estimate |
|---|---|---|---|
| M23 | **Economy checks on every pull request** | M13 (can start any time after) | 6 h |
| M24 | **AI-agent training environment** (Gymnasium API) | M17; uses an impact score built here | 7 h |
| M25 | **Self-writing world wiki** with dev-only private pages | M21 (report renderer) | 7 h |
| M26 | **Economics and politics lessons** from the game itself | M17-M20 (levers), M25 (links) | 6 h |
| M28 | **Bug reports that replay themselves** | none (better after M23) | 5 h |
| M29 | **Courts for broken contracts** | M17 (debts, credit), M25 (case law pages) | 8 h |
| M30 | **Tamper-evident world log** (no blockchain needed; see [BLOCKCHAIN.md](BLOCKCHAIN.md)) | M20 (mint and burn) | 4 h |
| M31 | **One-person-one-character safeguards** | M29 for juries; multiple players in the engine | 8 h |
| M32 | **Elections and a campaign-finance register** | M20 (lobbying), M31 (graph tracing) | 6 h |
| M48 | **Legitimacy and levy evasion** | M13 (better after M19) | 6 h |
| M49 | **Beliefs and rumours** | M13 | 7 h |
| M52 | **Policy stress tests** with attacker bots | M23, M31.2 | 6 h |
| M56 | **Unpaid guards turn bandit** | M48 | 5 h |
| M57 | **Amnesty and debt jubilee** | M17, M48; M56 and M19 for amnesty | 4 h |
| M59 | **Respectful play** (evidence in [RESEARCH.md](RESEARCH.md#m59-respectful-play)) | M23, M31 (bot league); M52 for the attacker report | 6 h |
| M27 | Docs, examples and v0.3.0 tag | all | 1.5 h |

- **Total:** about 92.5 h, roughly 12 working days; plan for **15 days** with the usual overrun.
- **How to build each one:** [BUILD_GUIDE.md](BUILD_GUIDE.md) breaks every milestone into
  issue-sized tasks with files, tests and pitfalls.
- **Fastest win:** M23 needs nothing from v0.2 beyond the bug fixes, so it can be built first if
  the repo goes public before v0.2 is done.
- **Can start any time:** M48 and M49 need only v0.1's levy, guard wages and prices, so they can
  run in parallel with v0.2. M56 follows straight on from M48.
- **Cut order if behind:** the wiki's graph view (keep the pages), the agent leaderboard (keep the
  environment and baselines), lesson count (ship 4 lessons, not 8), M52's grid search (keep the
  attacker bots and their report).

## M23: economy checks on every pull request (6 h)

**Goal:** every pull request that touches `scenarios/`, `src/questless/` or a config gets an
automatic comment such as:

> **Economy impact** (10 seeds × 5 scenarios, against `main`)
> - Price index in Iron Shortage: **+8%** (significant)
> - Hungry NPC-days in Drought: **2.1×** (significant)
> - Recovery after Mine Disaster: **3 days faster**
> - Contracts posted: no significant change · Invariants: all pass · Determinism: unchanged hash for unchanged scenarios

**Design:**
- **New command:** `questless diff --base <git-ref> [--seeds 10]`. It checks the base out into a
  temporary git worktree, runs the same scenario × seed grid on both trees, and writes
  `economy-diff.md` and `economy-diff.json`.
- **Metrics:** price index per good, hungry NPC-days, shortage days, recovery days, contracts
  posted and delivered, coin held by each sector, invariant failures.
- **Noise handling:** runs are paired by seed, so each metric gets a paired difference with a
  spread across seeds. A change is flagged as significant only when it exceeds the seed-to-seed
  noise (for example, the mean paired difference is more than 2 standard errors from zero).
  Everything else is reported as "no significant change", so reviewers aren't spammed.
- **Hard failures (red check):** any invariant failure; a state hash that changes for a scenario
  the pull request didn't touch while the engine is unchanged (accidental non-determinism).
- **Soft gates (configurable):** `.questless/ci.toml` can set limits such as "hunger may not rise
  more than 20% in any scenario"; breaking one makes the check fail with the evidence.
- **GitHub Action:** `.github/workflows/economy.yml` runs on `pull_request`, posts or updates one
  sticky comment with `gh pr comment --edit-last`, and uploads the charts as artifacts. Budget:
  under 3 minutes on a standard runner (the full grid is about 50 runs of 120 days at about
  0.2 s each).
- **Reusable outside this repo:** the action takes the scenario directory as an input, so a
  studio could point it at its own tuned scenarios.

**Accept when:** a pull request that halves farm output gets a comment flagging hunger in
every scenario; a docs-only pull request gets "no significant change"; a deliberately
non-deterministic change fails the check.

## M24: AI-agent training environment (7 h)

**Goal:** Questless as a standard reinforcement-learning and LLM-agent environment, scored by
real impact rather than coin.

**Design:**
- **Package:** `questless.gym`, behind an optional extra (`uv sync --extra gym`, which installs
  `gymnasium`). Registered as `Questless-IronShortage-v0`, `Questless-Drought-v0` and so on.
- **Observation:** a dictionary with
  - the open contracts (kind, good, quantity, reward, days left, requester);
  - each contract's chain as structured evidence records (kind, metric, value, baseline,
    threshold, day), not prose;
  - market prices and stocks, and the player's wallet and inventory.
  A text rendering is also available for LLM agents (`render_mode="text"`).
- **Actions:** `noop`, `accept(i)`, `buy(good, qty)`, `caravan(good, qty)`, `deliver(i)`,
  `abandon(i)`, `advance(days)`. Invalid actions are masked (an action mask in `info`), so agents
  don't waste training on impossible moves.
- **Reward (impact score):** compared with the same seed and no player actions,
  - **plus** hungry NPC-days and shortage days prevented;
  - **minus** bankruptcies and local producers' lost sales caused.
  Coin profit is reported but not rewarded, so the benchmark rewards helping the world rather
  than farming it. A `reward="profit"` option exists for comparison.
- **Second task, "explain":** the agent is shown a contract and must name its root cause and the
  steps in between; it is scored against the engine's own chain. This tests causal reasoning
  directly.
- **Baselines:** random, the existing scripted player, and a greedy "most reward first" agent,
  with their scores in `docs/AGENTS.md`.
- **Leaderboard:** results are deterministic, so a submission is just a save file; anyone can
  replay it and confirm the score.

**Accept when:** `gymnasium.utils.env_checker.check_env` passes; the same seed and actions give
the same reward; the scripted player beats random on impact in every scenario.

## M25: self-writing world wiki with private pages (7 h)

**Goal:** each run writes an Obsidian-compatible knowledge base: one Markdown page per notable NPC,
guild, site, good, shock and contract, cross-linked with `[[wiki links]]` through causes and
lineage, so Obsidian's graph view shows the economy's history.

**Visibility tiers (privacy by construction):**

| Tier | Who sees it | Examples |
|---|---|---|
| `public` | Everyone, including players | Posted contracts, public prices, shocks once announced, guild notices, delivered outcomes |
| `player` | One player, about themselves | Their own wallet history, contracts, impact score |
| `dev` | Developers and live-ops only | NPC wallets and traits, hidden causes (fog of cause), smugglers' identities, enforcement plans, seeds, thresholds, RNG state, other players' data |

- **Generated as separate vaults:** `wiki/public/`, `wiki/players/<id>/` and `wiki/dev/`. The
  public vault is rendered from a **redacted view** of the world, so private data is never written
  into it at all; it isn't merely hidden by a viewer. Links from public pages to private facts
  render as "unknown" rather than leaking that a page exists.
- **Every evidence record and field gets a visibility tag** in the engine (default `dev`, so new
  fields are private until someone decides otherwise).
- **Tests:** a leak test plants unique marker values in every private field and asserts that none
  of them appears anywhere in the public or other players' vaults.
- **Real players' personal data** is pseudonymous in every tier and lives only in that player's
  vault and the dev vault, so it can be deleted on request.
- **The dev tier is split by role** (economy designer, live-ops, trust and safety, security), each
  seeing only what its job needs, and every access to dev pages is logged. M42 makes this
  testable; [PRIVACY_AND_IDENTITY.md](PRIVACY_AND_IDENTITY.md) has the full design.

**Staying small at MMO scale (millions of players):**
- **The wiki is a cache, not a source of truth.** Any page can be regenerated from the save file
  (scenario + action log, about 9 KB per simulated year), so pages can be deleted and rebuilt
  freely.
- **Pages only for notable things.** An entity gets its own page only when it appears in a
  contract chain, crosses a salience threshold (a bankruptcy, a record price) or is a guild,
  site or shock. Ordinary NPCs and players appear only as lines in daily and monthly digests.
- **Compact pages:** YAML front matter for facts plus a few lines of rendered prose, with a size
  budget (about 2 KB per page) enforced by a test. Repeated wording comes from templates and
  isn't stored twice.
- **Sharding:** pages are stored under folders by type and id prefix (`npc/03/npc-0342.md`) so no
  folder holds more than a few thousand files.
- **Incremental:** after each simulated day only pages that changed are rewritten.
- **Retention:** daily digests roll up into monthly pages after 90 days.

**Accept when:** the public vault for every scenario contains no planted private marker; the
365-day baseline wiki is under 5 MB; opening the vault in Obsidian shows the shock linked to its
contracts, and contracts linked to their parent contracts.

## M26: economics and politics lessons from the game itself (6 h)

**Goal:** players learn real-world economics and politics from what happened in *their* world,
in the spirit of real research on game economies:
- Edward Castronova's study of EverQuest's economy (*Virtual Worlds*, 2001), which estimated its
  output per player like a country's GDP;
- the economists CCP employed to publish EVE Online's monthly economic reports (money supply,
  faucets and sinks, inflation);
- epidemiologists' use of World of Warcraft's 2005 "Corrupted Blood" outbreak to study how
  people behave in an epidemic (Lofgren and Fefferman, *The Lancet Infectious Diseases*, 2007);
- Lehdonvirta and Castronova, *Virtual Economies: Design and Analysis* (MIT Press, 2014).

**Two parts:**

1. **A monthly economic report, written from the run** (like EVE's). Money supply, money created
   and destroyed by source, a price index, the most valuable trade routes, who profited from each
   crisis, and how players actually behaved (what they accepted, what they ignored, how they
   sourced goods). It uses only public-tier data, so it's safe to publish in-game.
2. **Lessons** that each pair a real concept with a moment from the run. The engine finds the
   moment; the lesson explains it and asks the player to act. Each has a question, a lever and a
   measured answer from the chain, so lessons can be graded automatically.

| Lesson | Real-world concept | Where it shows up in Questless |
|---|---|---|
| Why prices spiked | Supply shocks, elasticity | Mine collapse → ore price chart |
| Starving next to full shops | Amartya Sen's entitlement theory of famine (*Poverty and Famines*, 1981): hunger from lost purchasing power, not lack of food | Mine Disaster poverty trap (REVIEW B3) |
| Imports that hurt local workers | Trade and local producers, "Dutch disease" | Caravan imports undercut smiths (RESULTS finding) |
| Why guilds exist | Collective action and mutual insurance (Mancur Olson) | Guilds on/off experiment |
| Printing money | Inflation, central banking, the Taylor rule | M20 central bank |
| Hedging a harvest | Futures, risk transfer, speculation | M18 futures |
| Prohibition and smuggling | Black markets, enforcement costs | M19 smuggling |
| Bailouts and moral hazard | Relief, credit, who pays | M17 relief and loans |

- **Politics lessons** use levers that exist by then: the town levy (taxation), guild lobbying of
  the central bank, enforcement budgets, and (if built) an elected mayor.
- **Skills practised:** reading a chart, separating cause from correlation, budgeting, pricing
  risk, and arguing for a policy with evidence.
- **Format:** each lesson is a Markdown page in the public wiki plus a guided mode in the
  dashboard. Teachers get an answer key in the dev tier.
- **Honesty rule:** each lesson states where the model is simplified (one town, rule-based NPCs)
  so it doesn't teach false precision.

**Accept when:** each lesson's "moment" is found automatically in its scenario on every seed (or
the lesson says it didn't happen); every claim in a lesson re-verifies against the chain.

## M28: bug reports that replay themselves (5 h)

**Goal:** a bug report is a file that reproduces itself. It holds the save (scenario, action log,
state hash: about 9 KB per simulated year) plus a machine-checkable observation of what looked
wrong ("tools price ≥ 60 on day 74").

- `questless repro bug.json` replays the world and says **reproduced**, **not reproduced**
  (probably fixed) or **replay mismatch** (the engine changed; it prints the command to replay on
  the reporter's version).
- `questless bisect bug.json` runs `git bisect` with `repro` as the test and names the commit
  that introduced the bug.
- `--emit-test` turns the report into a regression test.
- The dashboard gets a "Report a bug" button, and GitHub gets an issue template asking for the file.
- In a live game, reports are dev-tier (M25) with pseudonymous player ids.

**Accept when:** a planted bug reproduces, reads "not reproduced" after the fix, and bisect finds
the planted commit.

## M29: courts for broken contracts (8 h)

**Goal:** disputes over late, short or abandoned contracts are settled by a court that uses only
verifiable evidence. It teaches simplified versions of real contract law:
- offer, acceptance and consideration;
- performance bonds as security;
- breach and expectation damages, measured as the cost of buying substitutes ("cover");
- liquidated damages;
- the duty to mitigate;
- force majeure (a verified shock excuses performance);
- burden of proof and limitation periods;
- "loser pays" vs "each side pays" cost rules;
- recusal for conflicts of interest;
- appeal, and precedent published as case law in the wiki.

Clear cases are decided automatically, contested ones by an NPC magistrate, and (with multiple
players) by a seeded jury of players. Judgements are paid from the bond, then the wallet (keeping
an exempt floor), then recorded as debt. It's a game mechanic, not legal advice.

**Accept when:** a delay during a verified bandit shock is excused; the same delay without a shock
pays damages equal to the measured cover cost; conservation holds; rulings replay exactly.

## M30: tamper-evident world log (4 h)

**Goal:** blockchain's useful property (nobody can quietly rewrite history) without tokens,
wallets or a chain. Daily roots hash-chain the journal and state; Merkle proofs let a player check
their own balance; scheduled shocks are committed in advance and revealed later (provable
fairness); `questless audit` finds the first tampered day. An optional interface lets a studio
publish roots anywhere public. The reasoning is in [BLOCKCHAIN.md](BLOCKCHAIN.md).

**Accept when:** editing one journal entry in a save is detected on that day, and a changed shock
fails the reveal check.

## M31: one-person-one-character safeguards (8 h)

**Goal:** make multiboxing and bots pointless and visible in the economy. Real identity checks
belong to account and payment systems, outside this engine.
- Support many players in the engine.
- A bot league with deliberately colluding alts.
- Ledger-graph signals (one-sided trades, circular flows, value funnelled to one account).
- Behaviour signals (timing regularity, identical action sequences).
- Design levers that remove the payoff (per-person caps, non-transferable rewards, diminishing
  returns on repeated jobs).

**Accept when:** colluding alts are flagged on most seeds, the false-positive rate for honest
players is reported, and every flag re-verifies.

## M32: elections and a campaign-finance register (6 h)

**Goal:** every coin spent to influence policy is public. The town elects a mayor who sets the
levy and enforcement budget within bounds, and guilds lobby the central bank (M20). Every donation
to a campaign or lobbying fund is an ordinary ledger transfer with a `donation` reason, so the
register can't be incomplete.

Simplified real-world rules, each a config knob and a lesson for M26:
- **Disclosure threshold:** donations above N coin are published with the donor's name;
  smaller ones are reported only as totals (privacy for small donors).
- **Contribution limits** per donor, per election.
- **Spending limits** per campaign, or none (a teaching comparison).
- **"Dark money" detection:** coin routed through intermediaries (an NPC, a shell account or a
  player's alt) to dodge limits is traced with M31's transfer-graph signals and flagged with an
  evidence chain.
- **Conflict-of-interest view:** each mayoral decision lists the donors who benefit from it,
  measured from the ledger (who gained income after the change).
- **Cooling-off period:** officials can't take paid contracts from big donors for N days after
  leaving office.

**Public by design:** the register is in the public wiki tier (M25). Breaking the limits is a
claim the court (M29) can hear.

**Accept when:** the register's totals equal the ledger's donation transfers every day; donations
routed through an alt to exceed the limit are flagged on most seeds; the dashboard shows each
policy decision with its beneficiaries and their donations.

## M48: legitimacy and levy evasion (6 h)

**Goal:** the town's authority is a stock that can run down. Legitimacy is the share of NPCs who
comply with the town, between 0 and 1. Unpaid guard wages and long hunger lower it; paid wages and
full stomachs slowly rebuild it. Low legitimacy means NPCs evade the upkeep levy, the town collects
less, fewer guards are paid, and legitimacy falls again: a spiral the causal chain can explain from
start to finish, with every step re-measurable.
- **Where it runs:** tick step 3, right after guard wages, so today's unpaid wages count today. It
  builds on the wage rotation for an underfunded town (#52).
- **No new money:** evaded coin simply stays with the NPC. The ledger needs no new operation, and
  conservation is untouched.
- **Off by default:** baseline results and state hashes don't change until a scenario turns it on.
- **Feeds later work:** smuggling (M19) can rise as legitimacy falls, mayors (M32) can campaign on
  it, the invisible border (M53) measures it per site, and M26 gets a lesson on state capacity.

**Accept when:** a `legitimacy_spiral` scenario (a town that starts short of coin) shows the spiral
on most of 10 seeds; its chain links unpaid wages, legitimacy and evasion in at least three steps
that all re-verify; the baseline is unchanged with the feature off.

## M49: beliefs and rumours (7 h)

**Goal:** NPCs and guilds act on what they believe, not on the true state. Each keeps a believed
price and shortage per good, with the day it learned it and who told it. Merchants carry news
between sites with a delay, so beliefs lag reality, and a quest can be posted for a shortage that
has already ended.
- **The chain shows both:** "the Blacksmiths Guild believed ore cost 31 (told by a merchant on day
  40)" next to "measured: 18 on day 44". Both are evidence and both re-verify: the belief against
  the belief record, the truth against `measure()`.
- **Zero delay is today's engine:** with the delay at 0 every belief equals the truth, so v0.1
  results are reproduced exactly.
- Promotes the "Imperfect information and rumours" backlog idea. Fog of cause (detective quests)
  and told history (M50) build on it.

**Accept when:** a "false alarm" scenario posts at least one quest for a shortage that had already
ended, its chain shows belief and truth side by side, and every number re-verifies; with the delay
at 0 the baseline hash is unchanged.

## M52: policy stress tests (6 h)

**Goal:** before a tax, levy or enforcement change ships, scripted players try to break it. A
policy is a TOML change to a scenario; attacker bots (from M31's bot league) search for ways to
profit from it, and the result goes into M23's pull-request comment: "bot `wait-and-claim` gains
14 coin a day under this change; here is the replay."
- **Attackers** are small, documented strategies over the public player actions: claim and wait,
  buy before a known shock, corner a good, funnel value through alts. Each attempt is a replayable
  action log.
- **Findings are evidence:** each exploit comes with its seed, the saved replay and the ledger
  flows that show who lost.
- A bot like this would have found the transport-contract bug (#43), where a player was paid in
  full for hauling nothing.

**Accept when:** the attacker suite finds a deliberately planted exploit on most seeds and nothing
on the baseline, and the M23 comment links a replay for each finding.

## M56: unpaid guards turn bandit (5 h)

**Goal:** bandits start inside the world. Today the bandit shock comes only from a scenario file.
With M56, a guard left unpaid for too many days in a row deserts and turns bandit. Bandits cut
transport capacity and steal part of what is hauled, so merchants earn less, the levy shrinks, and
more guards go unpaid. The chain behind a transport contract no longer stops at "bandits on the
road": it continues to the deserters, their unpaid wages and the town's budget.
- **Theft is a transfer:** stolen goods move from the hauler to the bandit's account with reason
  `theft`, so conservation holds and every stolen unit is traceable.
- **Shocks from the world:** the bandit shock is an ordinary shock whose source is `world`, with a
  factor set by the number of active bandits. It replays like any other shock.
- **The way back:** bandits return to the guard roll after N paid days or through an amnesty
  (M57).
- **Off by default:** scenario bandits work exactly as today.

**Accept when:** in the legitimacy spiral scenario (M48), desertions appear on most seeds; a
transport contract's chain walks from the bandit shock to the deserters' unpaid wages and the town
treasury, and every step re-verifies; conservation holds with theft on.

## M57: amnesty and debt jubilee (4 h)

**Goal:** a ruler can cancel debts to buy back legitimacy, and everyone can see who paid for it.
Historical rulers did this, from Babylonian debt-cancellation edicts to Solon's reforms in Athens. A
jubilee writes off obligations in the M17 registry that match a rule (all debts, debts of NPCs in
poverty, or debts older than N days). An amnesty pardons bandits (M56) and smugglers (M19), who
return to their old work.
- **Who loses:** cancelling a debt moves no coin; the creditor's claim is written off. The chain
  lists each creditor's loss, measured from the registry, so the cost of the policy is never
  hidden.
- **What it buys:** legitimacy rises by a config amount scaled by the share of debtors relieved.
- **What it costs later:** lenders can price in the risk of future jubilees (M17 credit and loan
  rates), which an experiment measures.
- **Who decides:** a town policy rule in config first; the mayor (M32) can trigger it as a
  decision once elections exist. Both are recorded with evidence.
- **A lesson for M26:** debt relief versus moral hazard, measured rather than argued.

**Accept when:** conservation and the registry stay consistent through a jubilee; the creditors'
losses in the chain equal the written-off amounts; an experiment over paired seeds reports the
effect on legitimacy, hunger and later loan rates, with and without a jubilee.

## M59: respectful play (6 h)

**Goal:** players feel rewarded, but never feel they must give up work, family or friends to keep
up. M59 turns that into a check. It runs M31's bot league with players on different schedules and
fails the economy check (M23) when a change makes being away costlier, or rewards streaks, fixed
appointments or short windows. The design rests on peer-reviewed evidence collected in
[RESEARCH.md](RESEARCH.md#m59-respectful-play).

**Measure the pressure to play, not the hours.** Studies that link play logs to well-being find
little or no effect of time played, and hard time caps have a weak record. The harm comes from
play that feels compulsory. So M59 never caps or penalises hours. It measures what creates
obligation.

**Schedule bots**, each with the same strategy and a different life:
- the **daily grinder**, who plays every day;
- the **parent**, 30 minutes a day;
- the **shift worker**, four days on and three days off, at changing times;
- the **weekend player**, two long sessions a week;
- the **returner**, who plays daily, leaves for three weeks, then comes back.

**What the check measures**, per schedule bot, at equal hours played:
1. **Reward per hour played**, and its spread across schedules (**schedule fairness**). The
   weekend player's reward per hour must stay within a bound of the grinder's.
2. **Cost of absence:** what the returner lost while away, beyond the play it missed (reputation
   lost to contracts that lapsed, prices and offers that ran out, places on the board taken).
   Today a lapsed contract costs its full reputation reward, the same as abandoning it.
3. **Streak dependence:** the share of rewards that depend on playing on consecutive days.
4. **Short windows:** the share of contracts and offers that close in less than a week or have no
   catch-up path. Today every contract has a 10-day deadline (`contracts.deadline_days`).
5. **Appointments:** rewards available only at a fixed time, and group contracts that fail or pay
   less when one member is away.
6. **Paid randomness:** any random reward schedule tied to play time or spending. Contract rewards
   are escrowed, fixed and visible before a contract exists; the check keeps it that way.

**Levers**, each a config knob, so studios can see what fixes a failing check:
1. **Hand back without blame:** giving an accepted contract back before half its time has passed
   costs no reputation, and a contract that lapses costs less than one abandoned late.
2. **Catch-up paths:** fixed-time events leave a later way to earn the same reward.
3. **Asynchronous group contracts:** each member's share can be delivered on any day in the
   window, and no group is penalised for one member's absence.
4. **Diminishing returns on grinding:** repeated identical jobs pay less within a day (shared
   with M31's anti-bot levers).
5. **Natural stopping points:** sessions sized to an evening, and an optional, judgement-free play
   summary with player-set goals.

**Accept when:** on the baseline, every schedule bot's reward per hour stays within a configured
bound of the grinder's, and the returner's cost of absence stays below a second bound; a pull
request that adds a planted daily streak bonus fails the M23 check with the evidence; a planted
paid random reward fails it outright; and each measure's report cites the research finding it is
based on.

## M27: docs, examples and v0.3.0 (1.5 h)

- README sections for CI, agents, wiki and lessons, each with a one-command example.
- `docs/AGENTS.md` (benchmark rules and baselines) and `docs/TEACHING.md` (lesson guide for
  teachers).
- Changelog; tag v0.3.0.

## v0.4 scope: the megaserver foundations

Status: **in scope, planned after v0.3** · added 2026-10-21

The target is one shared world for every player (a megaserver at EVE Online's scale), in a
fantasy or a science-fiction setting, on one planet or across a galaxy. The full architecture is in
[BLUEPRINT.md](BLUEPRINT.md). v0.4 builds the parts that can be proven at small scale: many
regions in one world, a map and ecology that respond to the economy, fair automation, player
quests and diplomacy. Three milestones from the
[#53 idea bank](https://github.com/Adiezc/questless/issues/53) (M53-M55) let borders, colonies
and long supply chains emerge from the same ledger.

### Build order

| # | Milestone | Depends on | Estimate |
|---|---|---|---|
| M33 | **Theme packs and world topology** (fantasy and sci-fi; one planet or a galaxy) | v0.2 | 6 h |
| M34 | **Regions and simulation level of detail** | M33 | 14 h |
| M35 | **A map shaped by the economy** | M34 | 10 h |
| M36 | **Ecology and the commons** | M34; M29 and M32 for community rules | 8 h |
| M37 | **Legal automation: standing orders** | M31 (multiple players) | 12 h |
| M38 | **Players post quests** | M31, M37 | 6 h |
| M39 | **Treaties, sanctions and embargoes** | M34, M19, M29, M32 | 10 h |
| M40 | **Surrogate fast-forward experiment** | M34 | 8 h |
| M53 | **The invisible border** | M34, M48 | 6 h |
| M54 | **Civilization DNA** | M34 (the mutation can be built earlier) | 6 h |
| M55 | **Infrastructure dependency maps** | M34 | 8 h |
| M58 | **Fairness for late joiners** (evidence in [RESEARCH.md](RESEARCH.md#m58-fairness-for-late-joiners)) | M17, M31; M34 for migration between regions | 8 h |
| M60 | **Land and mine claims** (returns on capital; see [VALIDATION.md](VALIDATION.md#d2-coin-concentrates-to-real-world-levels-but-not-through-capital)) | none; M58 builds on it | 7 h |
| M61 | **Spoilage and storage** (time costs goods) | none | 6 h |
| M62 | **Know-how that rusts and is taught** (idle workers lose skill; apprentice contracts) | none; better after M61 | 7 h |
| M63 | **Players hire NPCs** (a labour market with escrowed wages) | M17 (obligation registry); M31 for more than one employer | 8 h |
| M64 | **Tool rental** (capital without ownership) | none; better after M60 | 6 h |
| M65 | **Scrap and recycling** (worn tools come back as iron) | none | 6 h |
| M66 | **Market fair days** (a weekly fair with outside traders) | none; better after M61 | 5 h |
| M82 | **Co-operatives against companies** (worker-owned firms next to investor-owned ones; evidence in [RESEARCH.md](RESEARCH.md#m82-co-operatives-against-companies)) | M60, M63; M17 for loans | 10 h |
| M41 | Docs, both skins in the dashboard, v0.4.0 tag | all | 3 h |

- **Total:** about 160 h, roughly 20 working days; plan for **26 days**.
- **Critical path:** M33 → M34 → M35/M36/M39/M53-M55. M37 and M38 can run in parallel once M31
  lands.
- **Cut order if behind:** the surrogate experiment (M40), sanctions (keep treaties and
  embargoes), new towns being founded in M35 (keep road growth).

## M33: theme packs and world topology (6 h)

**Goal:** the same engine runs a fantasy continent or a galaxy, with nothing setting-specific in
code.
- **Theme packs** (`themes/fantasy.toml`, `themes/scifi.toml`): display names, descriptions and
  flavour text for goods, professions, places, routes, shocks and evidence templates. Iron ore
  becomes rare metals, caravans become freighters, the mine collapse becomes a reactor failure.
- **Topology:** places and routes become a graph in the scenario (nodes with a type and position,
  edges with a travel time and capacity) instead of three fixed sites. A planet is a dense graph
  with slow edges; a galaxy is clusters linked by jump lanes.
- **Accept when:** the Iron Shortage scenario runs in both skins with an identical state hash
  (the skin changes words, not outcomes), and a test fails if code contains a setting-specific
  name.

## M34: regions and simulation level of detail (14 h)

**Goal:** many settlements in one world, each with its own market and prices, and three levels of
detail that never break conservation.
- **Regions** each have NPCs, a market and a ledger section; goods, coin and people move between
  them as messages through a transit ledger with travel time (the existing caravan mechanism,
  generalised).
- **Levels of detail:**
  - **full:** every NPC simulated (regions with players or active contracts);
  - **aggregate:** production and consumption per profession group, not per NPC;
  - **dormant:** frozen, then fast-forwarded on the aggregate model when visited.
- Switching levels moves holdings between individual and pooled accounts through the ledger, so
  it can't create or destroy value.
- **Lazy generation:** regions are created from the world seed when first reached, like No Man's
  Sky's planets.
- **Accept when:** conservation holds across regions and transit every day; a region switched
  full → aggregate → full keeps its totals exactly; prices differ between regions and trade
  narrows the gap; a 1,000-region world with 10 active regions runs a day in under a second.

## M35: a map shaped by the economy (10 h)

**Goal:** roads form where trade actually flows, like paths worn across a park, and towns grow or
shrink with their jobs.
- **Roads:** each route's capacity follows a smoothed average of the volume shipped along it. Busy
  routes are upgraded (a funded construction contract); unused ones decay to tracks. A new route
  can be built between two places when enough goods take the long way round.
- **Towns:** population moves toward regions where wages beat the cost of living, after a delay.
  A region over a job threshold founds a new settlement nearby; one that falls below a minimum
  is abandoned and becomes ruins (which M35 records for later seasons).
- **Provenance:** every road and town has a "why does this exist" chain ("built on day 212 after
  340 units a day travelled this way for 30 days").
- **Output:** map data (nodes, edges, sizes, history) that a renderer or a generative 3D tool can
  turn into terrain and buildings.
- **Accept when:** a road between two regions with a persistent price gap grows on every seed;
  a region whose only industry is shocked loses population; every road and town re-verifies.

## M36: ecology and the commons (8 h)

**Goal:** renewable resources (fish, forests, game; algae fields or atmospheric harvest in
sci-fi) can be overharvested, and communities can govern them.
- **Populations** follow a standard logistic growth model: they regrow fastest at half their
  carrying capacity, and harvesting beyond regrowth shrinks them. Collapse below a minimum
  population can be permanent.
- **Open access by default:** with no rules, producers harvest as much as pays, which leads to the
  "tragedy of the commons".
- **Community rules** follow Elinor Ostrom's design principles for governing commons, each built
  from existing parts:

  | Ostrom's principle | How the engine implements it |
  |---|---|
  | Clear boundaries | Who may harvest is a list in the region's charter |
  | Rules fit local conditions | Quotas and seasons set per resource |
  | Users make the rules | Changes are votes (M32) |
  | Monitoring | The ledger records every harvest |
  | Graduated sanctions | Fines that grow with repeat offences |
  | Cheap conflict resolution | Claims go to the court (M29) |
  | Nested governance | Region rules sit under treaty rules (M39) |

- **Accept when:** open access collapses a fishery on most seeds; a quota near the sustainable
  yield keeps it alive; the comparison is an M26 lesson.

## M37: legal automation, standing orders (12 h)

**Goal:** players write standing orders for their character in a small, sandboxed rule language,
so automation is a feature everyone has on equal terms and a cheating bot gains nothing.

```
when price(iron_ore) < 12 and stock(iron_ore) < 20:
    buy iron_ore 10
when contract.open(kind = "guild order", good = tools) and stock(tools) >= contract.qty:
    accept and deliver
limit 5 actions per day
```

- **Same limits for everyone:** every character has the same daily action budget, whether actions
  come from a person, a standing order or an AI agent. A bot can't act faster or more often than
  the official tool.
- **Public information only:** rules can read only what the player could see (public prices, their
  own holdings and contracts), never hidden state.
- **Sandboxed:** a hand-written parser and interpreter, no `eval`, a fixed evaluation budget per
  day, and deterministic order. (WebAssembly is the scale-up path in the blueprint.)
- **Logged:** every fired rule becomes a normal logged action, so replays, audits and courts treat
  it like any other.
- **Accept when:** a malicious rule (infinite loop, hidden-state access, oversized action) is
  rejected or stopped by its budget; standing orders replay exactly; in the bot league, a scripted
  "bot" with unlimited speed earns no more than the same strategy as standing orders.

## M38: players post quests (6 h)

**Goal:** players fund contracts under the same rules as NPCs.
- `post_contract(good, qty, reward, deadline)` escrows the reward first, then goes through the
  same validation: deduplication per player and good, cooldowns, per-person caps, feasibility.
- **Provenance** separates what's verified from what's stated: the player's stock and the market
  price are measured; "for my workshop" is a stated reason, labelled as such.
- **Anti-abuse:** a small posting fee (a coin sink); contracts accepted by a poster's own alts are
  flagged by M31; quests can't pay out more than was escrowed.
- **Accept when:** a player-posted quest and an NPC quest for the same good are handled
  identically by validation; a laundering attempt through an alt is flagged.

## M39: treaties, sanctions and embargoes (10 h)

**Goal:** regions (or player nations) make agreements with real economic effects.
- **Treaties** are contracts between governments with clauses for tariffs, free passage, shared
  resource quotas (M36) and arbitration. Each side escrows a bond; breaches go to an arbitration
  court (M29), like international trade disputes.
- **Embargoes** block trade on named routes or with a named region. The price gap they create
  triggers smuggling (M19) predictably, and the chain says so.
- **Sanctions** block transfers with named accounts. Their real effect (who actually lost income,
  including the side imposing them) is measured against a replay without the sanction.
- **Accept when:** an embargo produces a smuggling route on most seeds; a sanction's measured
  cost appears for both sides; a broken treaty clause pays from the bond.

## M40: surrogate fast-forward experiment (8 h)

**Goal:** test, honestly, whether a learned model can fast-forward dormant regions.
- Train a simple model (start with linear regression in `experiments/`, with numpy as an extra)
  on Questless runs to predict a region's next-day aggregates from today's.
- Measure its error against the full simulation over 30, 90 and 365 days, with and without
  shocks.
- Design the safety net: the ledger still enforces conservation, so the surrogate predicts
  *flows* that the ledger applies; large errors trigger a switch back to the aggregate model.
- **Accept when:** the write-up reports where the surrogate works and where it fails, with the
  numbers. A negative result is a valid outcome.

## M53: the invisible border (6 h)

**Goal:** a border is wherever a town's authority actually reaches, not a line drawn on a map. For
each site and region, *reach* is measured from the ledger: the share of the levy actually
collected there (M48), how often paid guards patrol it, and how much of its trade pays the town's
market tax. Where two towns' reach overlaps, the border sits where one overtakes the other.
- **Borders move:** an unpaid garrison or a new road (M35) shifts them, and the map shows the
  change with a chain explaining why.
- **Contested zones** are places no town reaches well. Smuggling (M19) thrives there, and towns
  can post patrol and collection quests to claim them.
- **No polygons:** the border is drawn from measured reach, so it can always be re-verified.

**Accept when:** in a two-town scenario, cutting one town's guard wages moves the border towards
it within a configured number of days on most seeds, and every border point on the map links to
the reach numbers behind it.

## M54: civilization DNA (6 h)

**Goal:** when colonists found a new settlement (M35), it inherits its parent's institutions with
small changes. The colony's config is a copy of the parent's (levy rate, guild rules, guard wage,
relief policy) with deterministic, bounded mutations, and it records its lineage.
- **Mutations** come from a `founding` RNG stream, within bounds set per knob in the scenario, so a
  run replays exactly.
- **Lineage** works like contract lineage: each settlement's wiki page (M25) shows its family tree
  and which rules it changed.
- **Selection is real:** settlements whose rules work grow and found more colonies; those that
  don't shrink (M35). Over a long run the map shows which institutions spread.
- **Can start before M34:** the `mutate()` function and its tests work on single-town scenarios
  today.

**Accept when:** colonies' configs differ from their parent's only within the declared bounds; a
long run replays to the same family tree; the report shows which rule variants spread and which
died out.

## M55: infrastructure dependency maps (8 h)

**Goal:** show how one broken link travels. When a bridge or road fails, the causal walk follows
its effects across regions: the bridge closes, ore stops crossing, smiths two regions away run
short, tools wear out, farms produce less, and a town far from the bridge goes hungry. Each step is
evidence with a measure key.
- **Engine:** `causes.py` gets edges that cross regions through M34's transit ledger, and chains
  can be exported as a graph (nodes and edges as JSON).
- **Dependency view:** for any site, a ranked list of the links whose loss would hurt it most, from
  forked replays that cut each link in turn.
- **Quests:** the most critical links attract funded maintenance and bypass contracts before they
  fail, with the counterfactual as evidence.
- **Can start before M34:** exporting today's single-town chains as a graph is useful on its own
  (M15's map, M25's wiki).

**Accept when:** cutting one bridge in a three-region scenario produces a chain that crosses at
least two regions and re-verifies at every step, and the dependency view's top-ranked link matches
the largest loss in the forked replays.

## M58: fairness for late joiners (8 h)

**Goal:** a player who joins in year 10 can still do well. In a world that has run for a decade,
newcomers face incumbents who have had years to build wealth, reputation, land and influence. M58
measures that head start, shows where it comes from, and gives designers levers that keep it
within a bound without driving veterans away. The levers and their defaults rest on peer-reviewed
evidence collected in [RESEARCH.md](RESEARCH.md#m58-fairness-for-late-joiners).

**Measure at equal time played, not equal calendar date.** Bot players with the same strategy join
on day 0 and on day 3,650 and are compared after the same number of days played:
- the **income gap** at equal tenure, and the **time to a first worthwhile contract**;
- **access**: the share of the quest board a newcomer may claim;
- **concentration** (Gini, top 10% share) and **mobility** (how much wealth rankings change from
  year to year), plotted against each other across seeds, the game's own Great Gatsby curve;
- **r − g**: capital income against wage income, by asset type, since the evidence points to land
  and housing as the main long-run driver.

**Where the head start comes from**, reported separately so designers fix causes, not symptoms:
reputation gates, capital returns (M17, M18), land and claims, offices and donations (M32), and
better information (M49).

**Levers**, each a config knob, off in the baseline:
1. **A ledger-based progressive levy with no exemptions and no liability cap.** Real wealth taxes
   lose most to misreporting and exemptions; the ledger rules out the first, and the design rules
   out the second. Avoidance is measured as migration between regions (M34).
2. **A land value tax on claims**, which the game can value exactly from the unworked output of
   each claim.
3. **A resource dividend:** mine royalties paid equally to every character, as Alaska does.
4. **Guild entry fees and licences** with a real quality signal, so the trade-off between
   protection and exclusion is measurable.
5. **Residents voting on building permits** (M32, M35) in growing towns, with a residency period
   before newcomers can vote.
6. **Apprentice and mixed newcomer–veteran group contracts**, because the evidence says early
   exposure and contact with better-off peers matter most.
7. **A starting grant** for every new character, graded inversely to family wealth once
   dynasties exist, and funded by inheritance tax.
8. **Reputation that weights recent work**, and **paid mentors** measured by their mentee's
   results (with mobility checked, since mentoring can also pass advantage on).

**Accept when:** the income gap at equal time played stays below a configured bound across seeds;
veterans' reward per hour stays above a second bound; M52's attacker bots find no way to farm the
newcomer levers with alts; and each lever's report states the research finding it is modelled on
and what the model leaves out.

## M60: land and mine claims (7 h)

**Goal:** wealth can earn more wealth. Today NPCs can only earn by working, so coin stays far more
equal than real wealth ([VALIDATION.md, D2](VALIDATION.md#d2-coin-concentrates-to-real-world-levels-but-not-through-capital)),
and r − g, the main long-run driver of wealth concentration in the research
([RESEARCH.md, M58](RESEARCH.md#m58-fairness-for-late-joiners)), can't be measured. M60 adds the
asset the evidence points to: land and mining rights.

**Design** (decided 2026-10-24):
- **Claims are work rights.** Every gatherer (miner, farmer) works one claim at their site. A
  claim has an owner and a worker; at genesis each worker owns the claim they work, so day 0 is
  as equal as it is today, and any concentration comes from trade.
- **Rent is a share of output.** A worker who doesn't own their claim pays the owner
  `rent_share` of the day's output, valued at the day's prices, in coin, after the market clears.
  A tenant never pays below `rent_floor` coin (subsistence), and the shortfall is forgiven and
  counted as `rent_unpaid`. Tenants are never evicted in this version.
- **Claims trade.** An owner whose coin falls below `sell_below` sells one claim and keeps working
  it as a tenant (a sale-leaseback). The buyer is the richest NPC who would still hold
  `buy_reserve` coin after paying. The price is `price_days` days of the claim's recent rent
  (rent share × its mean daily output value over the last 7 days). Coin moves on the ledger
  (reasons `rent` and `claim sale`), so conservation holds.
- **Off by default** (`[claims] enabled = false`). With it off, nothing changes and every state
  hash stays the same. Policy overlays may switch it on, so it can be an export arm.

**Measured:**
- `TickStats`: rent paid and unpaid, claims sold and their mean price, and the share of claims
  held by the richest 10% of NPCs.
- The export adds `claims_owned`, `rent_paid` and `rent_received` per NPC per day, and rent and
  claim sales per day, so a researcher can split income into capital (rent) and labour (sales and
  wages), which is r against g.

**Simpler than reality, on purpose:** claims are all equally productive (no Ricardian rent), no
eviction, no mortgages, and the population is fixed, so site capacity never binds. Each is a
config-free follow-up once the basic loop is measured.

**Accept when:**
- coin is conserved, and every claim always has exactly one owner and one worker;
- with claims trading, the baseline's wealth Gini (coin plus claims at their price) ends above a
  world whose claims never trade, across seeds. Coin alone isn't the measure: buyers turn coin
  into claims;
- with claims off, every scenario's state hash is unchanged;
- the export's per-NPC rent columns add up to the day's totals.

## M61: spoilage and storage (6 h)

**Goal:** holding goods has a cost. Today a sack of food kept for a year is as good as new, so
stockpiling is free and a drought can be waited out on old harvests. In real economies, storage is
where much of the work of fighting scarcity happens: granaries, cold chains, warehouses. M61 makes
food spoil and lets the town build storage that slows it down, so a drought chain can reach back
to "the granary was never built".

**Design:**
- **Spoilage is a daily rate per good.** Each good has a `spoil_rate` in `[goods.*]` (food spoils,
  ore and tools barely do). Every day, each account loses that share of its stock, with fractional
  units carried per account like production carry, so integer goods stay unbiased. Spoiled units
  leave through `ledger.consume` with reason `spoiled`, which is the `spoiled` term the goods
  balance in [PLAN.md](PLAN.md) already reserves. Conservation holds.
- **Escrow and transit are exempt.** Goods held for contracts or in caravans don't spoil, so a
  player is never punished for an obligation the engine itself holds.
- **Storage is a building.** A granary at the market or the farms multiplies the spoil rate there
  by `granary_factor` (for example 0.25) for up to `granary_capacity` units. Units above capacity
  spoil at the full rate. The town or a guild funds construction through an ordinary contract
  (players deliver the tools to build it), so storage competes with relief for the same treasury.
- **NPCs respond.** With spoilage on, `stock_days` targets for food are capped at the number of
  days before a unit loses half its value, so NPCs stop hoarding what will rot.
- **Off by default** (`spoil_rate = 0` for every good). With it off, every state hash is unchanged.

**Measured:** `TickStats.spoiled` per good, granary fill, and the share of each harvest that is
eaten, sold or lost. The export adds them per day.

**Evidence and chains:** a `spoilage` evidence kind with a measure key (units lost per day at a
site). The causal walk for a food contract checks whether stored food would have covered the
shortage without spoilage, and if so adds "food stocks spoiled faster than they were replaced",
linked to the missing or full granary.

**Simpler than reality, on purpose:** goods are fungible, so spoilage is a smooth rate, not
per-batch ages (item biographies would add those later). There's no salting, smoking or cooling
yet; each could be a recipe that turns food into a slow-spoiling good.

**Accept when:**
- goods are conserved with spoilage on, and every spoiled unit has a `spoiled` journal entry;
- with every `spoil_rate` at 0, each scenario's state hash is unchanged;
- in the drought scenario, a world with a granary has fewer hungry NPC-days than one without, across
  paired seeds;
- a food contract's chain includes spoilage only when the counterfactual (same seed, no spoilage)
  would have covered the need, and the evidence re-verifies.

## M62: know-how that rusts and is taught (7 h)

**Goal:** a crisis leaves scars. Today a smith idle for a month returns at full skill the day the
ore comes back, so every shock is fully reversible. Economists call the real effect *hysteresis*:
long unemployment erodes skills, so output stays low after the cause is gone. M62 makes skill grow
with practice and decay with idleness, and lets guilds pay masters to train apprentices, which
gives players a quest that rebuilds a town's capacity, not only its stock.

**Design:**
- **Skill has two parts.** `traits.skill` stays as the NPC's talent. A new `experience` value
  (0 to 1) multiplies it: `effective = skill × (floor + (1 − floor) × experience)`. Working days
  raise experience by `learn_rate` toward 1; idle days lower it by `rust_rate` toward 0. At genesis
  every NPC starts at `start_experience`.
- **Teaching is a contract.** When a guild's average experience for a profession falls below
  `teach_below`, the guild posts a training contract: the most experienced member teaches the
  least experienced for `teach_days`. The master's output falls by `teach_cost` while teaching, and
  the guild escrows the reward that makes up for it. A player fulfils the contract by delivering
  the practice inputs (ore for a smith) and the pair's food for the course. On completion the apprentice's experience rises by `teach_gain`.
- **Visible hysteresis.** A shock that ends no longer ends its effects. The engine records how long
  output takes to return to 95% of baseline after a shock ends, per profession.
- **Off by default** (`[knowhow] enabled = false`). With it off, every NPC's experience is 1 and
  every state hash is unchanged.

**Measured:** mean experience per profession per day, recovery time after each shock, and training
contracts posted and completed.

**Evidence and chains:** an `experience` evidence kind ("Smiths' average experience fell from 0.92
to 0.61 after 24 idle days"), measured from `TickStats`. The causal walk for a tools shortage that
outlives its ore shock walks back: tools output low ← smiths' experience low ← idle days ← the
ore shortage, so the chain explains why recovery is slow.

**Builds towards:** labour mobility in the backlog (NPCs who switch profession start with low
experience) and M58's apprentice contracts for players.

**Accept when:**
- with know-how off, every scenario's state hash is unchanged;
- in the mine disaster scenario, output recovers more slowly after the shock with know-how on than
  off, across paired seeds, and training contracts shorten that recovery;
- the training contract is fully escrowed and conserves coin and goods;
- the `experience` evidence re-verifies, and a forged value is reported.

## M63: players hire NPCs (8 h)

**Goal:** a labour market. Today players buy goods, but they can't buy work. Idle NPCs (no ore,
no demand) earn nothing while players lack hands. M63 lets a player hire an NPC for a wage, so
players compete with guilds and the town for workers, and wages become a price the economy sets.
It also gives players the first way to *start* production instead of only moving goods.

**Design:**
- **Hiring is a contract the player funds.** A player offers a daily wage for N days to an NPC.
  The whole wage bill is escrowed up front (an obligation in M17's registry), so a player can't
  hire what they can't pay. The NPC accepts if the wage beats their expected earnings from their
  own work over the last 7 days, plus a `switch_premium`. Ties break by seeded order.
- **What the player gets.** A hired NPC works their own trade with inputs the player supplies, and
  the output goes to the player's account instead of the NPC's. The NPC still eats, wears tools
  and pays the levy on their wage like any income.
- **Guild rules apply.** Guilds can set a minimum wage for members (`[guilds.*] min_wage`). A
  guild below its emergency threshold can't lose more than `max_hired_share` of its members, so a
  rich player can't empty a guild during a crisis.
- **Ending the job.** The contract ends at term, or early if the player stops supplying inputs for
  `quit_after` days. Unpaid escrow returns to the player; the wage already earned stays with the
  NPC. Every payment is a ledger transfer with reason `wage`.
- **Off by default** (`[hiring] enabled = false`). With it off, every state hash is unchanged.

**Measured:** NPCs hired per profession, the mean wage against each trade's expected earnings,
unemployment (idle NPCs who weren't hired), and the share of output produced for players.

**Evidence and chains:** a `hired` evidence kind. When a shortage follows a wave of hiring (smiths
hired away to make tools for a player, so farmers lack tools), the causal walk names the employer
and the wage, so the chain shows who outbid the town.

**Simpler than reality, on purpose:** one NPC, one employer; no strikes or negotiation (strikes and
unions are in the backlog); no firing before term except for missing inputs.

**Accept when:**
- coin and goods are conserved, and escrow equals the unpaid wages of live jobs every day;
- with hiring off, every scenario's state hash is unchanged;
- a player can't hire beyond their escrowable coin, or more than `max_hired_share` of a guild
  in crisis;
- an experiment over paired seeds reports the effect of hiring on idle NPC-days and on the price of
  the hired trade's output;
- the chain behind a shortage caused by hiring names the employer, and its evidence re-verifies.

## M64: tool rental (6 h)

**Goal:** a worker can use capital they don't own. Today a farmer who can't afford tools works at
`no_tool_factor` until they can, so a poor worker stays poor. In real economies, renting
equipment is how most people use capital: tractors, taxis, looms. M64 lets NPCs with spare tools
rent them by the day, so a rental market sits beside the market for tools themselves, and the rent
becomes a measured return on capital next to M60's land rent.

**Design:**
- **A rental is an obligation.** The owner moves one tool into a rental account; the renter uses
  it as if it were theirs. Each day the renter pays `rental_fee` coin (reason `tool rent`). If the
  renter can't pay for `default_after` days, the rental ends and the tool goes back to the owner.
- **The owner bears the wear.** A rented tool wears like any tool. When it falls below the
  replacement threshold, it is used up and the rental ends, so the fee has to cover wear. NPCs
  who rent out tools price that in: `fee = tool price × wear per day × (1 + rental_margin)`.
- **Who rents.** Each day, NPCs whose tools are below threshold and who can't afford a new tool
  but can afford the fee rent from the owner with the lowest fee, in seeded order. Owners rent out
  only tools beyond their own next replacement.
- **Players can be owners.** A `rent_out` action lets a player put tools on the rental market at
  their own fee, with the same rules.
- **Off by default** (`[rental] enabled = false`). With it off, every state hash is unchanged.

**Measured:** tools rented per day, mean fee against the tool price, NPC-days worked without
tools, and rent income by owner, which the export adds next to M60's land rent.

**Evidence and chains:** a `rental` evidence kind. When a farm shortage has workers without tools,
the walk now separates "no tools for sale" from "tools for sale but unaffordable, and no one renting
them out", so the chain names the missing market.

**Accept when:**
- coin and tools are conserved, and every rented tool is in exactly one rental account;
- with rental off, every scenario's state hash is unchanged;
- in the iron shortage scenario, NPC-days worked without tools fall with rental on, across paired
  seeds;
- an owner never rents out the tool they need for their own next replacement.

## M65: scrap and recycling (6 h)

**Goal:** a worn-out tool isn't just gone. Today replacing a tool destroys it. With M65 it
becomes scrap that smiths can melt into iron, so a mine disaster has a second supply line and the
price of scrap links to the price of ore. It's a small circular economy, and it teaches why
recycling rises when raw materials get expensive.

**Design:**
- **Scrap is a good.** Replacing a tool or weapon turns it into `scrap_per_tool` units of a new
  `scrap` good in the NPC's account (reason `scrapped`), instead of consuming it outright.
  Conservation still counts every unit.
- **Recycling is a recipe.** Smiths gain a recipe that turns `scrap_per_ore` scrap into one ore.
  They pick between ore and scrap by the margin per input, as they already pick between recipes,
  so recycling rises only when ore is expensive.
- **Scrap trades.** NPCs sell scrap at the daily market like any good. A scrap collector contract
  (R4) is posted when smiths are short of ore while scrap sits unsold at the farms, so players haul
  it.
- **Off by default** (`scrap_per_tool = 0`). With it off, no scrap appears.

**Measured:** scrap made, sold and melted per day; the share of smiths' iron that comes from scrap;
the scrap price against the ore price.

**Evidence and chains:** a `recycled` evidence kind. A tools contract's chain during a mine
disaster can show that recycling covered part of the gap ("scrap supplied 30% of smiths' iron
since day 18"), so the contract is smaller and the evidence says why.

**Simpler than reality, on purpose:** scrap doesn't wear and has one grade; there's no sorting or
pollution yet (the backlog's pollution and Pigouvian taxes idea can add it).

**Accept when:**
- goods are conserved, and every scrap unit traces back to a scrapped tool or weapon;
- with recycling off, every scenario's state hash is unchanged (see the pitfall on adding a good
  in the build guide);
- in the mine disaster scenario, tools output falls less with recycling on, across paired seeds;
- smiths melt scrap only when it is cheaper per unit of iron than ore.

## M66: market fair days (5 h)

**Goal:** time with a rhythm. Today every day's market is the same. Historical towns had weekly
markets and seasonal fairs where outside traders came with goods and money. M66 adds a fair every
`fair_every` days: outside merchants buy and sell at their own prices, so NPCs and players plan
around it, and prices rise and fall on a weekly pattern players can learn.

**Design:**
- **Outside traders join the market.** On a fair day, the `outside` account posts asks and bids at
  `fair_price_factor` of its own reference prices, up to `fair_volume` units per good. Trades go
  through the ordinary clearing, so they are ledger transfers like any other.
- **NPCs plan for it.** Gatherers hold back up to `fair_hold_days` of output for the fair when the
  last fair's price beat the daily price, and smiths stock ore before it. This is a small change
  to the existing stock targets, not new behaviour.
- **Fair fees fund the town.** Outside traders pay a stall fee (reason `fair fee`) to the town,
  so a fair is a source of town income that a bandit shock (M56) on fair day hurts most.
- **Players can plan.** The fair calendar is public and shown in the dashboard, unlike shock dates.
- **Off by default** (`[fair] every = 0`). With it off, every state hash is unchanged.

**Measured:** fair volume and prices against the days between fairs, the weekly price pattern, and
town income from fees.

**Evidence and chains:** a `fair` evidence kind. If a fair drained the town of food (outside buyers
paid more than locals), the chain behind the next food contract says so, with the volume exported
that day.

**Accept when:**
- coin and goods are conserved, and the outside account's balances move only on fair days and
  through caravans and exports;
- with fairs off, every scenario's state hash is unchanged;
- prices show a weekly cycle with fairs on and none with fairs off, across seeds;
- a food contract after a fair that exported food carries the `fair` evidence, which re-verifies.

## M82: co-operatives against companies (10 h)

**Goal:** players can found a worker co-operative (one member, one vote) next to an ordinary
investor-owned company in the same trade, and watch how each comes through a crisis. Decades of
research find the same pattern in Uruguay, Italy, France, Spain and the US: in a downturn,
co-operatives tend to cut pay and keep jobs, while conventional firms keep pay and cut jobs
([RESEARCH.md](RESEARCH.md#m82-co-operatives-against-companies)). M82 lets that difference
*emerge* from the members' votes, so players can test it, break it and learn why it happens.

**Two kinds of firm:**
- **An investor-owned company.** Owners hold shares in proportion to the capital they put in
  (claims from M60, tools, coin). It hires workers at a wage (M63). Profit goes to the owners.
  When demand falls, the owner decides; workers can't see the books, so wages are fixed and the
  firm adjusts by laying people off.
- **A worker co-operative.** Members put in a share each and work in the firm. Every member has
  one vote whatever their share. Pay comes from the day's surplus by a rule the members set, and a
  share of every surplus goes into an **indivisible reserve** that can be spent on the firm but
  never paid out to members. When demand falls, members vote: cut everyone's pay, spend from the
  reserve, or lay people off.

**Votes, not scripts:** each NPC member votes for the option that gives them the best expected
income, counting the chance that they would be the one laid off. Nothing in the code says "co-ops
keep jobs": if they do, it's because a majority preferred sharing the loss. A player can join and
campaign for the other option.

**The Mondragon layer (optional):**
- **A group of co-ops** can pool a share of their surpluses into a common fund and move members
  between co-ops when one is struggling, as the Basque Mondragon group does. When Mondragon's
  appliance maker Fagor Electrodomésticos collapsed in 2013, the group found places for many of its
  members in other co-ops; that's the kind of story the chain should be able to tell.
- **A pay-ratio cap** that members can vote to set, limiting the gap between the highest and lowest
  pay.

**The hard parts, modelled honestly:**
- **Raising capital is harder.** Co-ops can't sell voting shares, so they rely on members' shares,
  the reserve and loans (M17). Research finds their survival advantage shrinks once you account
  for the resources they start with.
- **Drifting away from the model.** A successful co-op can hire non-member workers instead of
  admitting new members, until few of its workers are owners. Researchers call this degeneration.
  M82 measures the member share of the workforce every day, so players can watch it happen or
  vote to prevent it.
- **Long crises hurt too.** Pay cuts protect jobs for a while, but a long slump drains the reserve
  and the members' patience. Recent Italian data finds co-ops' resilience fading in later years of
  prolonged stress.

**For the players:**
- **Founding a firm is a choice with a trade-off,** not a better or worse option: a company is
  quicker to finance and the owner decides alone; a co-op shares risk and power.
- **Votes are short.** One question, a few options, each with its expected effect on the voter's
  income, shown before they vote.
- **Rivalry is the fun.** A co-op and a company in the same trade compete for the same customers,
  workers and claims, and the economy check (M23) shows which did better in each scenario.

**Measured:** for each firm type, employment and pay volatility through shocks, survival, reserves,
the member share of the workforce, and the share of value added paid to labour. The experiment
runs paired seeds through the mine disaster and drought scenarios with co-ops, companies and both.

**Evidence and chains:** evidence kinds `firm_vote` ("The smiths' co-op voted 7 to 3 to cut pay by
12% rather than lay off 2 members") and `layoff`. A shortage chain can now walk to a firm's
decision and the vote or owner behind it.

**Off by default** (`[firms] enabled = false`). With it off, every state hash is unchanged.

**Accept when:**
- coin and goods are conserved, and the indivisible reserve can never be paid out to members;
- with firms off, every scenario's state hash is unchanged;
- no code path sets a co-op's employment directly: layoffs and pay cuts happen only through votes
  (co-ops) or the owner's rule (companies);
- across paired seeds in the mine disaster, the experiment reports employment and pay volatility
  by firm type, and the report states whether the research pattern appeared;
- the member share of each co-op's workforce is recorded daily;
- a `firm_vote` record re-verifies, and a forged tally is reported.

## M41: docs, both skins and v0.4.0 (3 h)

- A theme switch in the dashboard; a multi-region map.
- README and BLUEPRINT updates with measured results; changelog; tag v0.4.0.

## v0.5 scope: people, privacy and learning

Status: **in scope, planned after v0.4** · added 2026-10-21

A megaserver lives or dies by its community. v0.5 makes the world safe to join (privacy), easy to
talk in (a common language without leaving anyone out), worth playing *together* (steward NPCs)
and worth learning from (a skills passport). Two milestones from the
[#53 idea bank](https://github.com/Adiezc/questless/issues/53) (M50, M51) make history itself
something players learn to check: what NPCs say happened, against what the log proves.

### Build order

| # | Milestone | Depends on | Estimate |
|---|---|---|---|
| M42 | **Privacy as code** | M25, M30, M31 | 6 h |
| M43 | **Language bridge: English as a common language, with learning built in** | M25, M26, M33 | 8 h |
| M44 | **Steward NPCs: AI that keeps the world fun and pushes players together** | M24, M31, M37 | 12 h |
| M45 | **Skills passport** | M25, M26 | 6 h |
| M47 | **Skill tracks: eleven real-world subjects taught through play** | M26, M45, and each track's mechanics | 14 h |
| M50 | **Told history versus the log** (cultural memory and myths) | M49, M25 | 8 h |
| M51 | **Records that decay** | M50, M25, M30; M33 for institution names | 6 h |
| M69 | **Light check-ins by voice, and real breaks** | M37, M42, M59 | 8 h |
| M70 | **The weekly newspaper** | M25, M43; M49 for slanted papers | 6 h |
| M71 | **Play for everyone: accessibility and one-switch play** | none (dashboard checks can start now); M59 for the parity check | 10 h |
| M75 | **Offline basics** (a few safe things to do with no connection) | M37, M69; M24's local world for practice runs | 8 h |
| M79 | **Guilds on prescription** (gentle, time-limited guilds for lonely or isolated people, run with care partners) | M42, M44, M59, M69, M71 | 10 h |
| M81 | **Career tasters** (try a role in the game, then see the real jobs behind it; evidence in [RESEARCH.md](RESEARCH.md#m81-career-tasters)) | M33, M45, M47, M62, M71; M75 for practice runs | 10 h |
| M46 | Docs and v0.5.0 tag | all | 2 h |

- **Total:** about 114 h, roughly 14 working days; plan for **18 days**.

## M42: privacy as code (6 h)

**Goal:** the privacy design in [PRIVACY_AND_IDENTITY.md](PRIVACY_AND_IDENTITY.md) becomes rules
CI can check:
- a data inventory of every personal field (purpose, lawful basis, retention, tier) and a test
  that fails when a new player field isn't listed;
- role-based developer tiers (economy designer, live-ops, trust and safety, security), with every
  access recorded in the tamper-evident log (M30);
- personal data kept in a separate identity store, encrypted per player, so deleting a key erases
  a player without touching world history;
- retention jobs and a DPIA template.

**Accept when:** the inventory test catches an unlisted field; the leak test passes for every tier
and role; erasing a player in a save leaves the world hash chain valid and no personal data
recoverable.

## M43: language bridge (8 h)

**Goal:** one world with no language servers, where English is the common language and players
are helped to learn it, without excluding anyone who doesn't speak it yet.

**Why, from research:** studies of MMOs and language learning are encouraging, with caveats.
- Sylvén and Sundqvist (*ReCALL*, 2012) found that Swedish 11-12-year-olds who gamed more had
  better English; the study was correlational.
- Rankin, Gold and Gooch (2006) reported vocabulary gains for English learners playing
  EverQuest II, mainly through talking to NPCs; the sample was six people.
- Peterson (*ReCALL*, 2012) found that EFL learners' chat in an MMORPG showed signs of developing
  social and cultural competence in the language.
- Thorne, Fischer and Lu (*ReCALL*, 2012) showed that World of Warcraft's quest texts and fan
  sites are linguistically rich, often complex, reading.
- Thorne's work also notes that WoW's language-specific servers kept speakers of each language
  together. A megaserver with a common language puts learners in contact with everyone else.

**Design:**
- **Structured text translates exactly.** Contracts, causal chains, prices and UI are data, so they
  render identically in every language. A contract's terms can never be mistranslated.
- **Global channels default to English;** regional and guild channels use any language. Nobody is
  penalised for writing in their own language.
- **Bridge mode for chat:** the original message is shown with a translation underneath (the
  translation service is a pluggable adapter; the engine defines the message format and
  language tags).
- **Learning mode (opt-in):**
  - quest and NPC texts available in graded "plain English" versions, since game texts can be
    hard (Thorne et al.);
  - game vocabulary highlighted from the theme pack's glossary;
  - translation that fades to on-request as the player progresses;
  - a private vocabulary record (player tier).
- **Language-exchange contracts:** players pay or teach each other, using the mentor-contract
  mechanism.
- **Research hooks:** opt-in, anonymised data exports for language-learning researchers, approved
  through the transparent-experiments process.

**Sources:** [Sylvén and Sundqvist 2012](https://www.cambridge.org/core/product/47000F4B1842ED58569C99A94AAA59A5) ·
[Rankin, Gold and Gooch 2006](https://diglib.eg.org/handle/10.2312/eged.20061005.033-038) ·
[Peterson 2012](https://resolve.cambridge.org/core/journals/recall/article/abs/learner-interaction-in-a-massively-multiplayer-online-role-playing-game-mmorpg-a-sociocultural-discourse-analysis/47512049EFFC60C2C8C01C75A176518A) ·
[Thorne, Fischer and Lu 2012](https://cambridge.org/core/journals/recall/article/semiotic-ecology-and-linguistic-complexity-of-an-online-game-world/895B505C7298D7E1A1B8734AA0E3C8E2) ·
[on WoW's language-specific servers](https://arxiv.org/pdf/1502.02655)

**Accept when:** every evidence kind and UI string has an entry in at least two languages, with a
test; contracts render identically from structured data in each; learning mode can be switched
on and off per player; no feature requires English to play.

## M44: steward NPCs (12 h)

**Goal:** capable AI-driven NPCs whose job is to keep the world playable and fun, which can help
or hurt players, but which always leave the most rewarding play to humans working together.

**Roles:**

| Role | What it does | When it steps back |
|---|---|---|
| **Mentor** | Teaches new players the basics through small, real contracts | Once the player completes a group contract with humans |
| **Matchmaker** | Introduces players whose needs fit ("Mira the smith needs ore; Jun the miner has it") through linked quests | Never forces it; introductions are offers |
| **Understudy** | Fills an empty role in a region (no human smith, no trader on a route) so the economy keeps working | As soon as humans take the role; it can't undercut human prices |
| **Rival** | Antagonists (bandit lords, corrupt officials, pirate fleets) whose strength scales so groups beat them far more easily than solo players | Defeated, bought off or outvoted |
| **Caretaker** | Keeps markets liquid (buyer and seller of last resort) and the drama director's tension in its target band | When human trade is healthy |

**The rules they follow:**
- **Same rules as everyone:** ledger, escrow, action budgets (M37). They can't create coin or
  goods.
- **Every intervention has a "why":** steward actions are evidence records ("Matchmaker linked
  these quests because both players had been solo for 5 sessions"), visible to developers and,
  in summary, to players.
- **Labelled:** players know stewards are AI-controlled (AI Act Art. 50).
- **Optimised for health, not engagement:** steward goals measure fun and community (players in
  groups, new players' first successes, tension in band, inequality, market liquidity), never
  time spent. No manipulative techniques, no artificial scarcity of fun; they suggest breaks
  after long sessions.
- **Capable but auditable:** stewards' policies are trained offline in the agent environment
  (M24), frozen for a season and deterministic at runtime, so they replay and can be reviewed.
  Language models write their dialogue from verified provenance only; they never make decisions.
- **"Better together" rewards:** group contracts with complementary roles, bonuses for mixed
  groups of new and veteran players. Solo play stays viable but slower.

**Accept when:** in the bot league with simulated players, matchmakers and rivals raise the share
of players in groups without raising wealth inequality (paired seeds); understudies leave when
humans arrive; every steward action re-verifies.

## M45: skills passport (6 h)

**Goal:** players see which real-world skills they've practised, with evidence from their own
play. Details in [SKILLS.md](SKILLS.md).
- Skill detectors over verified actions ("opened a hedge before a verified shock" → risk
  management).
- Private by default; shareable as a signed, non-transferable credential.
- Each skill links to its lesson (M26).
- A teacher view for classes, with consent.
- No reward for repetition.

**Accept when:** each detector fires on a scripted example and not on a counter-example; the
passport never appears in the public vault; an exported credential verifies its signature.

## M47: skill tracks (14 h)

**Goal:** eleven real-world subjects taught through play, each a track of lessons (M26),
skills-passport entries (M45) and challenges. Details and the full list in
[SKILLS.md §4](SKILLS.md#4-skill-tracks).

| Track | Taught through |
|---|---|
| Economics | Shocks, prices, trade between regions |
| Investing and financial markets | Futures, shares in NPC startups, prediction markets |
| International relations | Treaties, sanctions, embargoes, migration between regions |
| Public policy | Referendum previews, policy experiments (UBI vs relief) |
| Politics and governance | Mayors, guild votes, the donation register, constitutions |
| Law | Courts, contract terms, the land registry |
| Leadership and project management | Group contracts, running a guild |
| Supply chains and operations | Transport, roads, disruptions |
| Data literacy and statistics | Causal chains, charts, forecasts scored for accuracy |
| Media literacy and research | Fact-checked player journalism, rumours |
| Behavioural economics and psychology | Bank runs, bubbles, rumours |

- **Per track:** a concept map (5-10 real concepts), at least three lessons with moment finders,
  passport detectors, one challenge, and a "what the model leaves out" note.
- **Built incrementally:** a track ships when the mechanics it needs exist; the economics and data
  literacy tracks can ship first because v0.1 already supports them.
- **Good for contributors with subject knowledge:** teachers, economists, lawyers and political
  scientists can write lessons without touching the engine.

**Accept when:** every track has its concept map, three lessons whose numbers re-verify, and
passport detectors with tests.

## M50: told history versus the log (8 h)

**Goal:** NPCs tell their own version of events, and players test the claims against the log. The
world keeps two histories: the objective one (the ledger and evidence, which never change) and the
told one (what NPCs say happened, which drifts as stories pass from mouth to mouth). This merges
three #53 ideas: cultural memory, world-written history and living myth-making.
- **Claims** are derived from real evidence: who told it, which event, the stated value and the day
  it was told. Each retelling distorts it by fixed rules (the mine collapse grows deadlier, the
  guild that helped gets more credit), so a claim can be wrong but never invented.
- **Spreading** reuses M49's network: claims travel with merchants and through guilds.
- **Fact-checking is gameplay:** a `fact_check` action compares a claim with `measure()` and pays
  for corrections, in the spirit of the "player journalism with fact checks" idea.
- **Myths:** claims that survive many retellings become named legends on the wiki (M25), each
  marked true, partly true or false, with the evidence.
- **Guardrail:** narration never rewrites state. A language model may phrase a claim, but its
  numbers and its event come from the record.

**Accept when:** every claim links to a real event; a fact check of a distorted claim recovers the
measured value; a long run produces at least one legend whose verdict re-verifies.

## M51: records that decay (6 h)

**Goal:** the in-world archive can be lost. The developer's log (M30) is permanent and
tamper-evident, but the town's own records are copies that wear out unless an institution keeps
them: a library, a body of scholars, an academy or a college (the name comes from the theme pack,
M33).
- **Upkeep:** each record has a condition that falls every day; a funded institution (wages paid
  through the ledger) restores it. An unfunded archive loses its oldest, least-used records first.
- **Lost records:** when a record goes, the wiki page for that event (M25) keeps only the told
  version (M50). History becomes what people remember.
- **Recovery quests:** a RECOVER contract finds a copy in ruins, an abandoned site or a distant
  region, and fulfilling it restores the record. This turns #53's archaeology idea into play.
- **A lesson** for M26 and the media-literacy track (M47): how much of what we know depends on who
  paid to keep it.

**Accept when:** with the institution unfunded, records are lost in the documented order and their
wiki pages fall back to told history; a recovery contract restores one; the M30 audit still
verifies the full developer log throughout.

## M69: light check-ins by voice, and real breaks (8 h)

**Goal:** nobody falls behind for having a life, and nobody feels they can't step away. Some
players have a few minutes on a commute; others go on holiday for two weeks with their family.
M69 lets the first group handle the basics by voice in a couple of minutes, and lets the second
group switch off completely without losing ground. It builds on M59, which already measures the
pressure to play: M69 adds the tools, and M59's check proves they don't create new pressure.

**Light check-ins:**
- **A short, fixed list of actions:** hear the board summary, accept or hand back a contract,
  change a standing order's limits (M37), and vote on a guild decision. Nothing else, so voice
  never becomes a second, faster way to play.
- **Speech becomes an action, never a decision.** A small on-device model maps what the player
  said to one action from the list with its parameters, reads it back ("Accept the ore contract
  for 12 units, reward 80 coin?") and waits for a yes. An unclear request does nothing. This
  follows the project rule that models may phrase things but never decide outcomes.
- **Voice stays on the device.** Audio and transcripts aren't stored or sent; only the confirmed
  action reaches the server, like any other action (M42).
- **The same reward for the same action.** A voice action pays exactly what the full client
  pays. M59's check gains a **voice-only bot**, and its reward per hour must stay within the same
  bound as everyone else's.

**Real breaks:**
- **Away mode.** A player sets the dates they'll be away. Their standing orders switch to a safe
  profile (keep supplying what's already promised, take on nothing new), contracts that would
  lapse are handed back without blame (M59's first lever), and nothing they own decays faster
  for their absence. Up to `away_weeks` a year, so it can't be used to freeze a position
  forever.
- **Quiet hours by default.** No notifications at night or in hours the player marks as family
  time. The default is on, and the game never asks the player to turn it off.
- **A weekly digest instead of pings.** One summary a week of what happened while they weren't
  looking (it can be the M70 newspaper), instead of a stream of alerts.
- **A welcome back.** On return, a short summary of what changed and one suggested first step.

**Accept when:** every voice action is one of the player actions and replays identically; an
unconfirmed or unclear request changes nothing; no audio or transcript leaves the device in the
default setup; M59's returner bot on away mode loses no more than a configured bound; the
voice-only bot's reward per hour stays within M59's schedule-fairness bound; quiet hours are on in
a new account.

## M70: the weekly newspaper (6 h)

**Goal:** a reason to look up from the board once a week. Every in-game week the world prints a
newspaper from its own log: what happened, why, and what it cost. Players who only have time to
read once a week still know their world, and every number in the paper can be checked.

**Design:**
- **Pages from the log.** Headlines are the week's biggest events by measured impact (shocks,
  shortages, contracts that saved or failed a town). A market page shows prices and weekly
  changes; a civic page covers guild votes, elections (M32), court rulings (M29) and the
  treasury. A people page names the players and NPCs behind the week's notable contracts, with
  their consent (M42).
- **Every number checks out.** Each figure links to its measure key and carries a "checked" mark
  from `verify()`. A language model may write the prose around the facts, from verified evidence
  only, and the text is stored, so the same week always gives the same paper.
- **Two papers, same facts.** Once M49 (beliefs and rumours) lands, a town can have two papers
  owned by rival guilds. They choose which verified facts lead and how to frame them, but they
  can't print a false number. Readers learn media literacy by comparing the two.
- **Players write too.** Players can submit articles. Each numeric claim must link to a measure
  key; claims that don't verify are marked, not deleted (the backlog's player journalism idea).
- **Read it anywhere.** A web page, a printable PDF, an email if the player asks for it, and an
  audio edition for listening (M71), in every language M43 supports.

**Accept when:** every number in a generated paper re-verifies and a forged one is reported; the
same week renders the same paper twice; two slanted papers of the same week report identical
values for every number they share; the paper passes M71's accessibility check.

## M71: play for everyone, accessibility and one-switch play (10 h)

**Goal:** anyone can play, whatever their body or mind. Questless has a head start: the world
moves one day at a time and every action is a choice, not a reflex. M71 turns that into a
guarantee and builds the rest: one-switch play, screen readers, eye tracking, colour-blind safe
charts and plain language. Players with disabilities are paid to co-design and test it; nothing
ships on the developers' guesses alone.

**Design:**
- **No timed inputs, by construction.** No action may require a response faster than
  `min_response_seconds`, and the world can be paused for a single player at any time. A test
  fails any action with a deadline shorter than that.
- **One-switch play.** The client offers a short ranked list of actions (the three most useful
  right now, then "more"). A scanning interface steps through it, and one switch, a single key,
  a sip-and-puff device or an eye-gaze dwell selects. Every action in the game is reachable this
  way.
- **Screen readers and keyboards.** The dashboard follows WCAG 2.2 AA and the Game Accessibility
  Guidelines: full keyboard use, labels for every control, text alternatives for every chart and
  map.
- **Seeing and hearing.** Charts use patterns and labels as well as colour; text scales; motion
  can be reduced; audio (M69, M70) has captions or a transcript.
- **Thinking and reading.** A plain-language mode (the backlog's reading-level selector), a
  "current goal" reminder, confirmation before anything costly, and undo where the rules allow.
- **Measured parity.** M59's harness gains a **switch bot** that plays only through the scanning
  interface. Its reward per hour must stay within the schedule-fairness bound.

Studios that did this well show it pays: *The Last of Us Part II* shipped with more than 60
accessibility options, and Microsoft's Xbox Adaptive Controller made one-switch and custom setups
standard hardware.

**Accept when:** an automated accessibility checker reports no serious violations on every
dashboard page; the switch bot's reward per hour is within M59's bound; every chart has a text
alternative and a non-colour encoding; no action has a deadline below `min_response_seconds`; at
least one round of paid testing with disabled players is written up in the docs.

## M75: offline basics (8 h)

**Goal:** people on a train, a plane or a farm with a weak signal can still take part. Offline
play is deliberately small: read the latest news of your world, plan, and queue a few simple
choices that the server checks when you reconnect. Nothing done offline can earn an advantage
over playing online, because nothing done offline takes effect until the server says so.

**What works offline:**
- **Read.** The client keeps a signed snapshot of what you last saw: your contracts, the board,
  prices, your guild, the latest newspaper (M70). It shows its age plainly ("as of 2 days ago").
- **Queue a few intentions.** Accept a contract if it's still open, hand one back, change a
  standing order's limits within the bounds you already set (M37), vote on an open guild
  question. That's the whole list, and it's capped at `offline_intents` a day.
- **Practise.** Because the world is deterministic, the client can run a private copy of your
  town forward from the snapshot to try ideas ("what if I supply ore for a week?"). Practice runs
  are marked as such and nothing in them carries over except what you choose to queue.

**Why it can't be exploited:**
- **Intentions, not actions.** Queued items are requests. On reconnect the server applies them in
  arrival order against the world *as it is now*, not as it was in the snapshot. A contract taken
  by someone else meanwhile is simply refused, with a plain message.
- **No trading offline.** Buying, selling, caravans and anything priced aren't on the list, so
  old prices can't be used against new ones.
- **The device clock isn't trusted.** Times come from the server on arrival. Changing the phone's
  clock, or queuing on several devices, gains nothing; duplicates are dropped.
- **No new information.** Practice runs use only the snapshot and seeded guesses for shocks; the
  real schedule of shocks is never on the device (the same rule that hides the shock schedule from players today).
- **Same reward, never more.** M59's harness gains an **offline traveller bot** that plays a day
  online, then three days offline with queued intents. Its reward per hour must stay within the
  schedule-fairness bound, and above the bot that does nothing while away.

**Accept when:** every queued intent is either applied or refused with a reason on reconnect;
nothing priced can be queued; a practice run never changes the server's state; a tampered
snapshot or clock gains nothing in M52's attacker tests; the traveller bot stays within M59's
bound.

## M79: guilds on prescription (10 h)

**Goal:** a kind place to belong, for people who need one. In the UK, the NHS employs social
prescribing link workers who can refer lonely or isolated people to community activities: a
walking group, a choir, a gardening club. M79 designs a guild that could be one of those
activities: gentle, small, time-limited and run with care partners, for older people, people who
are housebound, carers and anyone the link worker thinks it might help.

**What a prescribed guild is:**
- **Small and slow.** Six to ten people and a facilitator, meeting by voice (M69) or at a shared
  table (M76) at the group's own pace. Contracts are cooperative only: no rankings, no competition,
  no deadlines shorter than a week.
- **Time-limited, with a next step.** A cohort runs for `cohort_weeks` (about 12), like many
  community programmes. At the end, members can move into an ordinary guild together, keep meeting
  as a social group, or be signposted to local activities by their link worker. The game never
  tries to keep them.
- **Built for every body.** Large text, voice, one-switch play and plain language from M71 are on
  by default.

**Who runs it:**
- **Care partners** (charities, NHS link-worker services, councils, care homes) refer people and
  own the relationship. The game is a venue, not a health service.
- **Facilitators** are trained volunteers: people who want to volunteer, and psychology,
  social-work or occupational-therapy students, for whom it can count as supervised placement or
  volunteering hours where their university agrees.
- **Safeguarding first.** Facilitators are vetted (in the UK, a DBS check) and supervised by a
  qualified professional at the partner. Students never act as therapists. Every session has a
  clear way to raise a concern and to signpost crisis services.

**Privacy and health data:**
- **No health records in the game.** The referral happens outside the game. The game only knows a
  partner invited this player into a cohort; it never stores why (M42).
- **Measured by the partner, with consent.** Whether it helps is measured by the care partner or a
  university, with ethics approval, using validated loneliness and well-being questionnaires,
  outside the game and only for people who agree.

**Honest about the evidence:** reviews of social prescribing find promising but mixed results, and
the studies are often small. M79 is built so it can be properly evaluated, not assumed to work.

**Accept when:** a cohort can be created, joined by invitation only and closed at its end with a
choice of next steps; no field in the world log or player record holds a reason for referral;
facilitator tools include concern reporting and signposting; M71's accessibility check passes with
the cohort defaults; an evaluation protocol template for partners is in the docs.

## M81: career tasters (10 h)

**Goal:** a player tries a role in the game, enjoys it as play, and comes away knowing what the real
jobs behind it are like. The research ([RESEARCH.md](RESEARCH.md#m81-career-tasters)) is clear on
one point: a career game alone teaches little. What works is play, then reflection, then contact
with real people and real information, repeated over months. M81 builds that loop around ordinary
play, so the game stays a game.

**The loop:**
1. **Do.** "Try a week as a smith" drops the player into a real situation: the live world, or a
   practice copy of a live crisis for new players (M75). Real stakes, real shortages, nothing
   scripted.
2. **Notice.** At a natural pause (the end of a world day, never mid-action), the game may name
   one skill the player just used: "You planned production through a shortage." At most one a
   session, and it can be switched off.
3. **Reflect.** After the session, three short questions: what did you enjoy, what was hard, what
   surprised you? About a minute, always skippable, answers private unless the player saves them.
4. **Connect.** A "Then and now" card, outside the fiction, links what the player did to real
   jobs: the same and different tasks, pay ranges, and routes in (apprenticeships first, then
   college and degrees). Every figure shows its source and year and links to an official careers
   service.
5. **Talk.** The player can export a one-page taster report (what they did, which skills, what
   they thought) to bring to a careers adviser, a parent or a mentor.
6. **Meet.** Partner schools can attach real encounters to a taster: a video Q&A with a working
   welder or farmer, or a workplace visit.
7. **Repeat.** Tasters exist for every role. The next suggestion rotates through roles the player
   hasn't tried.

**Keeping it fun:**
- **Tasters are play, not lessons.** No quizzes, no pop-ups during action, no tutorial voice. The
  learning happens around the session, not inside it.
- **No grades and no verdicts.** Taster performance is never scored, ranked or compared, and the
  game never says "you should be a smith". It shows; the player decides.
- **No rewards for completing careers.** No points, badges or items for finishing tasters or
  answering questions: rewards turn reflection into box-ticking, and the evidence says thinking,
  not enjoyment or rewards, drives learning.
- **Optional, always.** A player who never opens a card loses nothing in the game.

**Fair to everyone:**
- **Suggestions never use gender or background.** The suggestion function has no access to them,
  and rotates every player through every role. Career games don't fix stereotypes by default, so
  the design has to.
- **Every role shows a range of people,** and non-degree routes sit alongside degrees, not below.

**Any setting, honestly:**
- **Cards attach to the engine's role, not the skin's name** (M33), so one card works for the
  fantasy smith and the sci-fi fabricator.
- **History is the bridge in fantasy:** most fantasy roles are ancestors of real ones, and
  apprenticeships began in medieval guilds, which M62's training contracts already mirror.
- **No honest match, no card.** A role with no real skill behind it (a dragon tamer) gets none;
  each card lists the shared activities that justify it, and a reviewer checks them.

**Content and data:** cards are short, hand-written files in the repo, one per role and country,
reviewed once a year, with links to official careers services for the details. Contributors can
write cards for their own country without touching code. ESCO skill tags can fill each card's
skills section automatically later; a full statistics pipeline is only worth building if a partner
needs it.

**Measured, not assumed:** a partner school runs a before-and-after evaluation with a follow-up
months later, with ethics approval and outside the game. The docs include the protocol.

**Accept when:**
- a taster runs in the live or practice world with no notices during action and at most one per
  session;
- reflection can be skipped and stores nothing unless the player saves it;
- every card figure shows a source and year, and every card lists the activities that justify it;
- no reward, score or ranking depends on tasters or reflection;
- the suggestion function takes no gender or background input, and every player is offered every
  role;
- the fantasy and sci-fi skins show the same card for the same role;
- the evaluation protocol is in the docs.

## M46: docs and v0.5.0 (2 h)

PRIVACY_AND_IDENTITY, SKILLS and BLUEPRINT updated with what was built; changelog; tag v0.5.0.

## v0.6 scope: a world connected to the real one

Status: **in scope, planned after v0.5** · added 2026-11-01

v0.6 connects the world to the one outside it. Real weather drives the seasons; the engine shows
what it costs in energy and does its heavy work when the grid is clean; other games feed their
shortages in as contracts; play contributes to real science, with players told when it does; the
map can sit on a real table; a world that shuts down stays alive as open data; idle devices help
research on clean power; and real towns can test a policy before they vote on it.
Each milestone keeps the five guarantees: real-world data enters only through the world log, so
every run still replays exactly with the network off.

### Build order

| # | Milestone | Depends on | Estimate |
|---|---|---|---|
| M67 | **Real weather, real places** | M30 (world log); M34 for many regions; better after M61 | 6 h |
| M68 | **Clean-energy simulation** (energy shown to players; heavy work when the grid is green) | M23, M34, M40 | 10 h |
| M72 | **Cross-game federation** (other games' shortages become contracts here) | M30, M34, M39; the backlog's Open Quest Protocol | 14 h |
| M73 | **Science from play** (your town in a paper; real citizen-science tasks) | M42, M45; the research export (v0.1) | 10 h |
| M76 | **A tabletop AR map** (the region on the kitchen table, for playing together) | M35, M55, M71 | 8 h |
| M77 | **Worlds never die** (a world that shuts down becomes open data anyone can restart) | M30, M42; M33 for replaceable assets | 6 h |
| M78 | **Idle devices do science on clean power** (opt-in volunteer computing) | M68, M73 | 6 h |
| M80 | **Play the policy before it becomes law** (a policy lab for real towns) | M23, M33, M40, M67; the backlog's referendum preview | 16 h |
| M74 | Docs and v0.6.0 tag | all | 2 h |

- **Total:** about 78 h, roughly 10 working days; plan for **13 days**.
- **Can start now:** M68's energy meter (M68.1) and M73's dataset citation (M73.1) need nothing
  from earlier versions.

## M67: real weather, real places (6 h)

**Goal:** the world's weather is the real weather somewhere. Each region is twinned with a real
place the designer picks. When that place has a dry month, the region has a drought; when a storm
crosses it, the roads close. Players can look up the real place and watch the same weather arrive.
It makes climate something players feel, and it's a natural lesson in data: how a rainfall
anomaly becomes a harvest.

**Design:**
- **A twin per region.** Region config names a public weather station or grid point and the
  source. The designer picks the place; the player's own location is never used (M42).
- **Weather becomes modifiers.** Rainfall against the place's normal sets farm output; storms set
  transport capacity; temperature sets spoilage (M61) and food need. The mapping is config, so a
  sci-fi skin can map the same data to solar flares or dust storms.
- **The log, not the network.** A separate ingest job fetches each day's weather and writes it into
  the world log (M30) before the tick, with its source, licence and a hash. The simulation reads
  only the log, so a replay never touches the network and gives the same hash.
- **A fallback that is honest.** If the feed is missing, the day is drawn from the place's
  historical normals with a seeded stream, and the log marks it as filled in.
- **Respect for real disasters.** Real weather can kill people. Designers can list events to
  soften or skip (`exclude_events`), and the default caps the in-game severity of any single day,
  so a real tragedy is never turned into a spectacle.
- **Open data only.** Sources must allow reuse (national met services' open data, open weather
  APIs); each record carries its licence.

**Evidence and chains:** a `weather` evidence kind ("Rainfall at the Seville twin station was 14% of
normal over 30 days, source and licence attached"). A drought chain now starts at a real-world
measurement.

**Accept when:** replay with the network off gives the same hash; a missing day falls back to
normals and is marked; the drought chain cites the station, source and licence and re-verifies;
with the feature off, every scenario's state hash is unchanged.

## M68: clean-energy simulation (10 h)

**Goal:** the engine uses clean power when it can, and everyone can see what the world costs. A
megaserver's simulation, experiments and model training draw real electricity. M68 measures it,
moves the heavy work to hours when the grid runs on wind, sun and water, and slows optional work
when it doesn't. Players see the energy their world uses, and the game rewards patience instead
of rewarding playing at certain hours.

**Measure:**
- **An energy meter.** Each run records CPU time by system (tick, contracts, provenance, wiki,
  experiments). An energy model turns it into kWh (hardware counters where the machine has them,
  a stated per-core estimate otherwise) and multiplies by the grid's carbon intensity for the
  server's region and hour, from a grid-data feed. The method and its error are documented next
  to every number.
- **What the world cost today.** The dashboard and the newspaper (M70) show energy and emissions
  per world day, per region and per kind of work, and the share that ran on low-carbon power.

**Schedule:**
- **Three kinds of work.** *Live* work (the tick players are in) always runs. *Deferrable* work
  (experiments, M23 sweeps, M40 surrogate training, wiki rebuilds, research exports, forecasts)
  has a deadline and runs in the cleanest forecast window before it. *Optional* work (extra seeds,
  precomputed views) runs only below an intensity threshold.
- **Level of detail follows the grid.** When the grid is dirty, dormant regions (M34) use the
  cheaper surrogate (M40); when it's clean, they run in full and catch up. The choice is logged,
  so replays use the same one.
- **Results never depend on timing.** The scheduler changes when work runs, never what it
  computes: the same inputs give the same hash whenever they run.

**Encourage, without pressure:**
- **A green queue for players.** Heavy requests (a 30-day forecast, a consequence-mirror replay,
  a big research export) cost less in-game coin if the player lets them wait for clean power. The
  result arrives later; nobody has to be online at a particular hour, so M59's appointment check
  still passes.
- **The world's own energy.** In the fantasy skin, towns can build windmills and water wheels; in
  sci-fi, solar arrays. They're ordinary infrastructure (M55) that lower the town's in-game costs,
  a small, honest mirror of the real transition.
- **Server targets in the open.** The studio publishes its clean-share target and the measured
  share each month, like the economy check publishes balance.

**Accept when:** every run reports energy and emissions with its method; replaying a recorded
week of real grid data, the scheduler moves at least `clean_shift_target` of deferrable work into
lower-carbon hours than running it at once; the same inputs give the same hash at any time of day;
the green queue passes M59's check.

## M72: cross-game federation (14 h)

**Goal:** different games, one connected world. A shooter, a farming game, a strategy game and an
economy game each stay their own game, made for the players who love that style, but they share
needs and consequences. A famine in a farming game becomes a supply contract here; a convoy that
shooter players defended reopens a road; a strategy game's treaty opens a border (M39). Every
kind of player contributes to the same story.

**What we learn from EVE Online:** CCP tried this with *Dust 514* (2013), a PlayStation 3 shooter
whose battles decided planetary control in EVE. It closed in 2016: the link was thin, few EVE
players felt it, and the shooter was on a different platform. CCP is trying again with *EVE
Vanguard*, a PC shooter set in EVE's universe. (*EVE Echoes* is a separate mobile game with its
own servers and economy, not a link to EVE Online.) The lesson for M72: the exchange must matter
to both sides every day, not only in rare battles.

**Design:**
- **A shared protocol.** The backlog's Open Quest Protocol becomes the federation format: a
  versioned JSON schema for contracts, deliveries, outcomes and evidence, with a validator and
  reference clients.
- **Bridges conserve value.** Each partner game has a bridge account with an escrowed balance and
  a daily cap. Goods and coin cross only through it, at rates set by trade, so no partner can
  create value from nothing. Conservation is checked on each side plus the bridge.
- **Signed, logged messages.** Every message is signed by the sending world and written to both
  worlds' logs (M30). Each side can replay alone from its log and get the same hash.
- **Chains cross worlds.** A contract that came from a partner carries the partner's evidence,
  verified with the partner's published measures, so "Why does this quest exist?" can answer
  "because a famine in the valley, in another game, on its day 212".
- **Quarantine.** A partner that sends forged or impossible messages has its bridge frozen
  automatically, with the evidence; M52's attacker bots try to break the bridge before anything
  goes live.
- **No real money, no tokens.** Federation exchanges in-game value only (see
  [BLOCKCHAIN.md](BLOCKCHAIN.md)).

**Proof at small scale:** two Questless worlds in different skins, plus a tiny reference "convoy
skirmish" game (a few hundred lines) whose results set a route-security factor here.

**Accept when:** conservation holds in both worlds and the bridges; each world replays alone from
its log with the same hash; a forged message is rejected and quarantines the bridge; a famine in
world A posts a funded contract in world B whose chain crosses worlds and re-verifies; the bridge
cap holds under M52's attackers.

## M73: science from play (10 h)

**Goal:** time in the world is fun, teaches something and contributes to something bigger, and
players know it. Two parts: the world itself becomes open research data, with players told when a
study uses their town; and real citizen-science tasks fit naturally into play.

**What already works elsewhere:** EVE Online's *Project Discovery* has had players classify cell
images for the Human Protein Atlas (2016), search telescope data for exoplanets (2017) and analyse
COVID-19 immune-cell data (2020). *Foldit* players have solved protein structures, *Eyewire*
players have mapped neurons, and *Borderlands Science* players have aligned gut-microbe DNA
sequences for researchers at McGill. The common thread: the task is real, scored against known
answers, and the game wraps it, not the other way round.

**Your town in a paper:**
- **Citable data.** Each public run export (v0.1's research export) gets a stable identifier and a
  citation file, so a paper can cite exactly which region and days it used.
- **A public study register.** Researchers register a study before running it (preregistration),
  with its question and the data slice. Players can read every study that uses their world.
- **Told when it matters.** When a paper is published, players whose actions appear in the cited
  slice get a notice and a "contributed to research" entry in their skills passport (M45), and the
  crisis's wiki page links to the paper. Players are pseudonymous in the data (M42), can opt out,
  and small groups are only released in aggregate.

**Citizen science in play:**
- **Real tasks, in-world.** A partner project's tasks (classifying images, checking sequences,
  spotting patterns) appear as an in-world activity: assaying ore samples or reading star charts in
  fantasy, scanning samples in sci-fi. Tasks come through an adapter for citizen-science platforms
  such as Zooniverse.
- **Scored honestly.** Rewards come from hidden known-answer items and agreement between players,
  so random clicking earns nothing and good work counts.
- **Modest rewards, never required.** Reward per hour stays at or below ordinary play, there are no
  streaks, and nothing in the world needs it (M59's check covers it). People do it because it
  matters, and the game shows them why.
- **Impact you can see.** A page per project shows what the community has done and what the
  researchers found, with links to their papers.
- **Data ethics.** Only partners with ethics approval and data released for public analysis.
  Player data never trains anyone's models without explicit opt-in.

**What it is not:** the economy simulation itself doesn't train health models; a game's moves
aren't medical data. The world's log is useful research data for economics and AI (M24), and
health research is served by embedding real tasks, as Project Discovery does.

**Accept when:** a known-answer check rejects random answers; the adapter never sends a player's
identity to a partner; M59's check passes with citizen science on; a test citation creates notices
only for opted-in players in the cited slice; every export carries its identifier and citation
file.

## M76: a tabletop AR map (8 h)

**Goal:** a world you gather around. With AR glasses or a phone, the region appears on the kitchen
table: towns, roads, caravans moving, a mine glowing red when it collapses. A family or a group
of friends sits around it together, points at a town and asks "why is this one hungry?", and
hears the chain. It turns play back into something social and in the same room, like a board game
night.

**Design:**
- **One map, many viewers.** Devices in the same room share one anchored map, so everyone sees the
  same thing in the same place. One person can play while others watch, or each plays their own
  character on the shared map.
- **The economy made visible.** Trade flows are lines whose thickness is volume (M35's roads),
  shortages are colours with patterns (M71), and dependencies light up when you touch a site
  (M55). Tapping anything opens its "why" chain, read aloud if you like.
- **The same game, not a new one.** The AR client uses the same public view and the same ranked
  action list as every other client (M71), so it has no special powers and no exclusive rewards.
- **Made for a session, then put away.** A table session has a natural end ("the week's market
  closes"), suggested when the group starts. M59's stopping points apply.
- **Privacy in the room.** Room scanning and camera images stay on the device; only the map's
  position on the table is shared between the devices in the room, and nothing reaches the
  server.
- **Open format.** The map is published as standard 3D scene data from the public view, so the
  community can build their own clients, and a plain 2D map always works for people without AR.

**Accept when:** the AR client reads only the public view and sends only ordinary actions; two
devices show the same map state for the same tick; no camera or room data leaves the device; every
AR view has a 2D equivalent; the shared map passes M71's colour and contrast checks.

## M77: worlds never die (6 h)

**Goal:** a world players spent years in never just disappears. When an online game shuts down,
everything its players built usually vanishes with it. The shutdown of Ubisoft's *The Crew* in
2024 started the *Stop Killing Games* campaign, a European Citizens' Initiative that passed a
million signatures in 2025. Questless can show the alternative in code: if a server shuts down,
its world becomes an open archive that anyone can verify and restart.

**Design:**
- **An ark export.** One command bundles the world log (M30), the latest snapshots, the scenario
  and config, the engine version and the hash chain into an archive. Any machine with the open
  engine can boot it and replay it to the published final hash, so the restarted world is provably
  the same world.
- **Nothing personal in it.** The world log holds pseudonymous ids and no personal data by design
  (M42), so it can be published. The export runs M42's scanner and refuses to finish if anything
  personal is found.
- **Players can come home.** Each player can download a signed key for their characters. On a
  restarted world, the key proves the character is theirs without revealing who they are. It's
  opt-in: characters nobody claims become ordinary NPCs, so towns don't empty.
- **Assets that can be replaced.** Third-party art and music may not be releasable. Because skins
  are separate from the engine (M33), an ark runs with the open default skin when an asset can't
  be shared.
- **A pledge in the repo.** A short `SUNSET.md` template that studios can adopt: what they'll
  release, how much notice players get, and how long the final archive stays up.
- **Drills, not promises.** CI builds an ark from a test world every week and boots it on a clean
  machine. A restart that doesn't reproduce the hash fails the build, so the promise is checked
  long before it's needed.

**Accept when:** an ark from a long run boots on a clean machine and replays to the final hash; the
export refuses to finish when a planted personal record is present; a player key claims its
character on the restarted world and nothing else; the weekly drill runs in CI.

## M78: idle devices do science on clean power (6 h)

**Goal:** a player's machine can help real research while they sleep. Volunteer computing has a
long record: Folding@home and BOINC projects have used donated computer time for protein folding,
climate models and astronomy, and from 2007 to 2012 Sony's PlayStation 3 ran Folding@home from its
home menu. M78 adds the same option to Questless clients, with one rule the old projects didn't
have: it runs only when the local grid is clean (M68).

**Design:**
- **Opt-in, off by default.** A player chooses to join and which project to support, from a list of
  vetted projects (M73's partners and established volunteer-computing projects).
- **Only when it costs nothing else.** Work runs only when the device is idle, plugged in and cool,
  and when the carbon intensity of the player's grid zone is below a threshold. The player gives
  their grid zone (a country or region they pick), never their location. Phones and laptops on
  battery are never used.
- **Honest about the cost.** It uses the player's electricity. The client shows the estimated energy
  and its cost at the player's own tariff before they opt in, and every month after. A daily cap is
  set by the player.
- **Sandboxed work.** Work units come through an established volunteer-computing client in its own
  sandbox; the game never runs arbitrary code from a project.
- **Recognition, not power.** Players see what their machine contributed and what the project
  found. Rewards are cosmetic and in the skills passport (M45) only, never coin or items: anything
  that buys power would turn electricity into an advantage and penalise players who can't afford
  it, and M59's check would fail.

**Accept when:** nothing runs without opt-in; no work runs on battery, while the device is in use,
or above the carbon threshold in a recorded week of grid data; the cost estimate is shown before
opting in; no in-game reward depends on computing contributed; M59's check passes with it on.

## M80: play the policy before it becomes law (16 h)

**Goal:** a town can see a policy's likely side effects before it votes. Before a real city changes
a tax, bus fares or parking rules, the policy lab runs the change in a model of the town, built
from the city's open data, and shows who is likely to gain and lose, with honest uncertainty. The
result feeds a public debate or a citizens' assembly. It informs a decision; it never makes one.

**Why this engine:** Questless already does the hard parts: exact replay, paired runs with and
without a change (the M23 economy check), and a "why" chain for every effect. Agent-based models are
already used in policy work, for example in housing-market research at central banks and in
epidemic planning. What Questless adds is that every result can be traced and re-checked.

**Design:**
- **A town from open data.** A modern-town theme pack (M33) maps population, jobs, household
  budgets, bus routes and fares from public statistics into a scenario. The mapping is a file anyone
  can read and challenge.
- **Paired runs, many seeds.** The lab runs the town with and without the policy across seeds and
  reports the distribution of effects by group (by area, income band, age band): who pays more,
  who travels less, what happens to local shops.
- **Backtest before trusting.** The lab first reruns a past policy in the same town (an earlier fare
  rise, say) and compares its estimate with what really happened. Results for a new policy are only
  shown alongside that backtest score, and a town whose backtest fails gets a warning, not a chart.
- **What the model leaves out.** Every report lists what isn't modelled, in plain words, next to the
  numbers.
- **Optional play.** Residents can play the policy in the town's twin. How players respond is
  reported separately from the model's estimate, as a signal of how people feel, not as a
  prediction.
- **Open by default.** Scenario, data mapping, runs and reports are published, so anyone can
  reproduce or contest them.

**Ethics:** partners are public bodies and universities; the lab never targets individuals; results
are never presented as forecasts without their uncertainty and backtest; and no political campaign
can commission a private run.

**Accept when:** a town scenario builds from a documented open-data file; a backtest of a past
policy reports its error against the real outcome; reports show effects by group with uncertainty
bands and the "left out" list; every run reproduces from the published files; a report cannot be
generated without a backtest result attached.

## M74: docs and v0.6.0 (2 h)

BLUEPRINT, RESEARCH and PRIVACY_AND_IDENTITY updated with what was built; changelog; tag v0.6.0.

## Idea backlog (not scheduled)

Scores are how likely a 2030s studio would ship each idea (1-10), followed by a rough effort.

| Idea | Score | Effort |
|---|---|---|
| Shock insurance paid out by verified evidence | 9 | 6 h |
| Shortage forecasts from forked simulated futures | 9 | 1 day |
| Crowdfunded repairs that fix the root cause | 9 | 6 h |
| Player-owned drone fleets (automation displaces merchants) | 8 | 6 h |
| NPC strikes and unions | 8 | 1 day |
| A profit-maximising NPC corporation that corners markets | 8 | 1 day |
| NPC memory and favours | 7 | 6 h |
| Reverse-auction contract claiming for many players | 9 | 6 h |
| Labour mobility: NPCs switch professions when broke | 9 | 1 day |
| Bot league: N scripted players competing, contention tests | 8 | 6 h |
| Sabotage contracts traced back to the saboteur | 8 | 6 h |
| Research grants: shortages drive new recipes | 8 | 1 day |
| An elected mayor: guilds vote on tax policy | 7 | 6 h |
| Seasons and climate cycles | 7 | 4 h |
| Imperfect information and rumours (now **M49**) | 7 | 1 day |
| Births, bankruptcy and business succession | 7 | 1 day |
| Contract feed for a companion app or Discord | 6 | 4 h |

### More creative ideas

| Idea | What it is | Score | Effort |
|---|---|---|---|
| Fog of cause (detective quests) | Part of a quest's causal chain starts hidden; players uncover links by visiting sites, questioning NPCs or buying data. Investigation becomes gameplay, and the full chain is the reward. | 9 | 1 day |
| Impact ledger | A counterfactual replay without the player's actions scores their real effect: "you prevented 41 hungry NPC-days and caused 2 bankruptcies". An accountability badge for every player. | 9 | 6 h |
| Drama director | A rule-based director (like Left 4 Dead's AI director) schedules shocks to keep economic tension inside a target band: never boring, never hopeless. | 9 | 6 h |
| NPC startups and angel investing | Idle NPCs pitch new businesses (a brewery, a tool repair shop) that add a recipe and a profession. Players fund them; the simulation decides whether they survive. | 9 | 1 day |
| Consequence mirror | An in-world shrine shows the "ghost" timeline where you didn't act, side by side with your own. Determinism makes alternate histories cheap. | 8 | 6 h |
| Escalation ladders | Ignored contracts escalate: unmet food leads to unrest, then strikes, then migration away from town. Each step posts bigger, rarer quests with full provenance. | 8 | 1 day |
| Item biographies | Crafted goods carry a short history (who mined the ore, who forged it, which crisis it was made in). "A crisis-forged tool from the Great Mine Collapse" becomes collectible. | 8 | 1 day |
| Depletion and prospecting | Mines run out over time; prospecting quests find new deposits. Sustainability becomes a long-term strategic layer. | 7 | 6 h |
| Morale economy | NPC morale affects productivity. Festivals (deliver food and ale) are quests that raise output, a "happiness GDP". | 7 | 6 h |
| Shard diplomacy (superseded by M34 regions on one megaserver) | Two server instances (or two scenario runs) trade by exchanging caravan files, so one world's shortage becomes another's export opportunity. | 7 | 1 day |

## Vision: what a 2030s MMO needs that a 2000s MMO didn't

| 2000s MMO | 2030s MMO | What Questless can own |
|---|---|---|
| Hand-written quest text | Quests caused by a simulated world | Funded, validated, explained contracts (v0.1) |
| Opaque economies, balanced by patch notes | Glass-box economies, balanced *before* release | Exact replay, `verify()`, economy tests on every change |
| Gold farmers found by bans after the fact | Exploits prevented by construction, audited by data | Escrow (no money from nothing), provenance trails |
| One server, one session, play at a desk | Cross-platform, asynchronous, watched by an audience | An open API and protocol, deterministic shared challenges |
| NPCs as vending machines | NPCs and AI agents as economic actors | An agent-ready environment with a verifiable "why" |
| A fan wiki written by players | A world that writes its own history, in every language | Chains as structured data, rendered into any language |

### Differentiators (each about a day on top of this repo)

| Idea | What it is | Score | Effort |
|---|---|---|---|
| **Economy CI for pull requests** (now **M23**) | A GitHub Action that runs the scenario suite on every change to a scenario or the engine, and comments on the pull request with an economy-impact diff (inflation, quest volume, hunger, recovery, against `main`). Balance changes get reviewed like code. | 10 | 1 day |
| **Daily Crisis** | A daily seed and shock that everyone plays. Determinism makes it fair; scores come from the impact ledger; replays are shareable proof. A Wordle-style ritual for economy players and streamers. | 9 | 1 day |
| **AI-agent gym** (now **M24**) | A Gymnasium-compatible environment (observation = board + chains, actions = player actions, reward = impact score), with baseline agents and a leaderboard. Questless becomes a benchmark for AI agents that must *reason about causes*, not just optimise numbers. | 9 | 1 day |
| **Open Quest Protocol** | A versioned JSON Schema for contracts, evidence and outcomes, plus a validator and example clients (Godot, Unity C# and a web widget). Any game can consume or emit explainable quests; the repo becomes the reference implementation. | 9 | 1 day |
| **Audience-driven world** | Viewers vote on the next shock (and players can bribe or counter-campaign); the world's explanations make the outcome readable on stream. The crowd acts as the weather. | 8 | 1 day |
| **Self-writing world wiki** (now **M25**) | A static site generated from a run: pages for every NPC, guild, shock and quest, cross-linked through provenance and lineage. The world documents itself. | 8 | 1 day |
| **Instant localization** | Evidence is structured data, so chains can render in any language from per-language templates (Spanish and German first), with tests that every evidence kind has a template. | 8 | 4 h |
| **Asynchronous companion play** | A webhook and contract feed so players take, source and deliver jobs from a phone or Discord between sessions, with a "quests that fit in 10 minutes" filter. | 8 | 1 day |
| **Real-money-trading detection** | Flag trades whose counterfactual impact looks like value transfer rather than commerce (persistently one-sided prices, circular flows), with evidence chains, like the anti-cheat for an economy. | 8 | 1 day |
| **Policy classroom** (folded into **M26**) | A mode for economics teaching: guided lessons ("cause inflation, then cure it"), with the central bank, futures and smuggling as levers and the chain as the answer key. A second audience beyond games. | 7 | 1 day |

### More 2030s ideas (not scheduled)

**Trust and fairness**

| Idea | What it is | Score | Effort |
|---|---|---|---|
| Provably fair world | Each day the server publishes a hash commitment of the next shocks and reveals the seed later, so players can check that developers didn't rig a crisis against them. | 9 | 6 h |
| Bug reports that replay themselves | Every in-game bug report attaches the save (about 9 KB). Live-ops replay the exact world state in seconds instead of guessing. | 9 | 4 h |
| Courts for broken contracts | Disputes over late or abandoned contracts go to a court of players, who rule using the evidence chain. Teaches due process and evidence. | 8 | 1 day |

**Politics and governance**

| Idea | What it is | Score | Effort |
|---|---|---|---|
| Referendum preview | Players propose policy changes (tax rate, enforcement budget) as TOML; before the vote, the economy CI from M23 simulates each option and publishes the predicted effects. Voting with evidence. | 9 | 1 day |
| A constitution file | The town's rules (who can tax, how mayors are elected, what the central bank may do) live in a versioned file that players amend by vote; every amendment has a diff and a history. | 8 | 1 day |
| Prediction markets on the world | "Will the mine reopen by day 60?" Markets settle automatically through `verify()`, so no one can dispute the outcome. Crowd forecasts become another data source. | 8 | 6 h |

**Economy design**

| Idea | What it is | Score | Effort |
|---|---|---|---|
| Inflation-indexed loot | Rewards and drop values follow the price index, so the classic MMO "mudflation" (items and gold losing value over years) can't happen. | 8 | 4 h |
| Pollution and Pigouvian taxes | Forges pollute nearby farms; players can lobby for a pollution tax or fund filters. Teaches externalities with a chain that shows who harmed whom. | 8 | 6 h |
| Historical shock packs | Scenarios modelled on real events (an oil shock, a hyperinflation, a bank run), each with a lesson comparing the game's outcome with what happened in history. | 8 | 1 day |
| Scenario marketplace | Players and designers publish scenarios; each carries an M23 economy-CI badge (stable, volatile, broken) so others know what they're getting. | 7 | 1 day |

### Society, law and money ideas (not scheduled)

**Institutions and accountability**

| Idea | What it is | Score | Effort |
|---|---|---|---|
| Freedom-of-information requests | Players file requests to release dev-tier facts (a guild's books, an enforcement plan) into the public wiki after a delay, unless a rule exempts them. Teaches transparency law with M25's tiers. | 8 | 6 h |
| Corrupt treasurers and audit quests | A guild treasurer sometimes skims; the ledger shows the gap between reported and real treasury; audit contracts pay players to prove it in court (M29). | 8 | 6 h |
| Campaign-finance register (now **M32**) | Lobbying (M20) and mayoral elections record every donation publicly through the ledger, so players can see who funded which policy. | 7 | 4 h |
| Player journalism with fact checks | Players publish news in the wiki; each numeric claim links to a measure key, and `verify()` gives the article a "checked" badge. | 8 | 6 h |

**Markets and money**

| Idea | What it is | Score | Effort |
|---|---|---|---|
| Guild banks and bank runs | Guilds take deposits and lend most of them out (fractional reserve); a rumour or shock can start a run, and the central bank's discount window (M20) is the lender of last resort. | 9 | 1 day |
| Land registry and mining claims | Sites have registered titles; claims can be bought, mortgaged (M17) and disputed in court (M29); the town can compulsorily purchase land for a road, with compensation. | 8 | 1 day |
| Price-control votes | Players vote on price ceilings during a crisis; the simulation shows the shortages and smuggling (M19) that follow, a classic economics result made visible. | 8 | 4 h |
| Universal basic income vs targeted relief | A toggle that pays every NPC a flat income (funded by the levy or the central bank) instead of relief quests; the experiment compares hunger, prices and quest volume. | 8 | 4 h |

**Scale and access**

| Idea | What it is | Score | Effort |
|---|---|---|---|
| Million-agent load harness | Headless scripted players (M31's bot league) at large scale to find where contracts, courts and the wiki stop scaling. | 8 | 1 day |
| Reading-level selector for chains | Every explanation in three registers: a one-line summary, the standard chain, and the expert view with metric keys. Helps younger players, language learners and economists alike. | 7 | 4 h |

### What a massive-scale 2030s MMO could be that no 2000s MMO was (not scheduled)

2000s MMOs froze time: characters never aged, the map never changed, players' choices reset every
patch, and anything automated was cheating. The ideas below drop each of those assumptions. Each
one builds on things Questless already guarantees (replay, provenance, escrow, tiers).

**A world with real time**

| Idea | What it is | Score | Effort |
|---|---|---|---|
| Dynasties instead of immortal characters | Characters age, retire and die; you play a family line. Inheritance, wills and inheritance tax make wealth a political question, and old money can't sit untouched for a decade. One player still controls one living character at a time. | 9 | 2 days |
| Seasonal worlds built on the ruins of the last | Each season's world ends in a finale and is archived. The next season is built on its ruins: players dig up items whose biographies name the players who made them, and the old season's case law and wiki become history books. | 9 | 2 days |
| A map shaped by the economy (now **M35**) | Roads appear where trade actually flows (like desire paths across a park), towns grow where jobs are and shrink where they aren't. The map becomes a picture of the economy's history. | 9 | 2 days |
| Ecology coupled to the economy (now **M36**) | Fish, forests and game animals have populations that reproduce and can be overharvested. Communities can govern them with rules in the style of Elinor Ostrom's work on commons, or watch them collapse. | 9 | 1 day |

**Players as institutions**

| Idea | What it is | Score | Effort |
|---|---|---|---|
| Legal automation instead of bots (now **M37**) | Players write standing orders for their character in a small, sandboxed rule language ("if ore is under 20 and the price is below 12, buy 10"). Everyone gets the same rate limits, so cheating with a bot gains nothing over the official tool. Rules are logged and replay exactly. | 10 | 2 days |
| Executable guild charters | A guild's rules (dues, payouts, voting, who can spend the treasury) are a small file the engine enforces. Members can read exactly what they're joining, and changing the charter needs the vote it describes. | 9 | 1 day |
| Players post quests too (now **M38**) | Players fund contracts under the same rules as NPCs: escrow first, deduplication, provenance. A player-to-player contract economy where every quest still explains why it exists. | 9 | 1 day |
| Treaties, sanctions and embargoes (now **M39**) | Player nations (towns or alliances) sign treaties backed by escrowed bonds. An embargo cuts trade and predictably creates smuggling routes; sanctions are measured by who actually lost income. | 9 | 2 days |

**Competition between whole worlds**

| Idea | What it is | Score | Effort |
|---|---|---|---|
| Migration between regions | On the megaserver, players and NPCs move between regions that run different policies. Regions compete for residents with taxes and services, a live version of Charles Tiebout's "voting with your feet" model. | 9 | 2 days |
| World-scale public goods | A server-wide threat (a flood in 30 days) needs a levee only everyone together can afford. Every contribution is public, free riders are visible, and the outcome depends on coordination, not combat. | 9 | 1 day |

**Open science**

| Idea | What it is | Score | Effort |
|---|---|---|---|
| Transparent experiments with an ethics board | The studio tests policies across regions openly: players see which experiments run where, an elected player panel approves them (like a university ethics board), and results are published. | 8 | 1 day |
| Paid mentors, measured by results | Veterans earn by coaching new players, paid by how much the new player's impact score improves, not by hours. | 8 | 6 h |
