# Roadmap: v0.2 to v0.5 build path

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
| M27 | Docs, examples and v0.3.0 tag | all | 1.5 h |

- **Total:** about 58.5 h, roughly 7.5 working days; plan for **9.5 days** with the usual overrun.
- **How to build each one:** [BUILD_GUIDE.md](BUILD_GUIDE.md) breaks every milestone into
  issue-sized tasks with files, tests and pitfalls.
- **Fastest win:** M23 needs nothing from v0.2 beyond the bug fixes, so it can be built first if
  the repo goes public before v0.2 is done.
- **Cut order if behind:** the wiki's graph view (keep the pages), the agent leaderboard (keep the
  environment and baselines), lesson count (ship 4 lessons, not 8).

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

**Goal:** QUESTLESS as a standard reinforcement-learning and LLM-agent environment, scored by
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

| Lesson | Real-world concept | Where it shows up in QUESTLESS |
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
quests and diplomacy.

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
| M41 | Docs, both skins in the dashboard, v0.4.0 tag | all | 3 h |

- **Total:** about 77 h, roughly 10 working days; plan for **13 days**.
- **Critical path:** M33 → M34 → M35/M36/M39. M37 and M38 can run in parallel once M31 lands.
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
  on QUESTLESS runs to predict a region's next-day aggregates from today's.
- Measure its error against the full simulation over 30, 90 and 365 days, with and without
  shocks.
- Design the safety net: the ledger still enforces conservation, so the surrogate predicts
  *flows* that the ledger applies; large errors trigger a switch back to the aggregate model.
- **Accept when:** the write-up reports where the surrogate works and where it fails, with the
  numbers. A negative result is a valid outcome.

## M41: docs, both skins and v0.4.0 (3 h)

- A theme switch in the dashboard; a multi-region map.
- README and BLUEPRINT updates with measured results; changelog; tag v0.4.0.

## v0.5 scope: people, privacy and learning

Status: **in scope, planned after v0.4** · added 2026-10-21

A megaserver lives or dies by its community. v0.5 makes the world safe to join (privacy), easy to
talk in (a common language without leaving anyone out), worth playing *together* (steward NPCs)
and worth learning from (a skills passport).

### Build order

| # | Milestone | Depends on | Estimate |
|---|---|---|---|
| M42 | **Privacy as code** | M25, M30, M31 | 6 h |
| M43 | **Language bridge: English as a common language, with learning built in** | M25, M26, M33 | 8 h |
| M44 | **Steward NPCs: AI that keeps the world fun and pushes players together** | M24, M31, M37 | 12 h |
| M45 | **Skills passport** | M25, M26 | 6 h |
| M47 | **Skill tracks: eleven real-world subjects taught through play** | M26, M45, and each track's mechanics | 14 h |
| M46 | Docs and v0.5.0 tag | all | 2 h |

- **Total:** about 48 h, roughly 6 working days; plan for **8 days**.

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

## M46: docs and v0.5.0 (2 h)

PRIVACY_AND_IDENTITY, SKILLS and BLUEPRINT updated with what was built; changelog; tag v0.5.0.

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
| Imperfect information and rumours | 7 | 1 day |
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

| 2000s MMO | 2030s MMO | What QUESTLESS can own |
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
| **AI-agent gym** (now **M24**) | A Gymnasium-compatible environment (observation = board + chains, actions = player actions, reward = impact score), with baseline agents and a leaderboard. QUESTLESS becomes a benchmark for AI agents that must *reason about causes*, not just optimise numbers. | 9 | 1 day |
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
one builds on things QUESTLESS already guarantees (replay, provenance, escrow, tiers).

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
