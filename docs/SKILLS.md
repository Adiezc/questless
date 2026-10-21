# Real-world skills: what players and developers can learn

Status: design, 2026-10-21.

A QUESTLESS-style world is a simplified economy, legal system and society that runs on real
rules. Playing it well, or building it, exercises skills that transfer outside the game. This
page lists them and how the project can make the learning deliberate rather than accidental.

Honesty first: research on games and learning is promising but mixed. Many studies are small or
correlational (they show that gamers know more, not that gaming caused it). The aim here is to
**design for** learning and measure it, not to promise it.

## 1. Skills for players

### Economics and money
- **Supply, demand and prices:** why ore costs triple after a mine collapse (v0.1, M14).
- **Budgeting and cash flow:** keeping a workshop solvent through a shortage.
- **Credit and debt:** interest, credit scores, why lenders ask for collateral (M17).
- **Risk management:** hedging a harvest with futures; insurance (M18, backlog).
- **Monetary policy:** what inflation is and how a central bank fights it (M20).

### Law, politics and civics
- **Contract law basics:** offer and acceptance, breach, damages, force majeure (M29).
- **Due process:** evidence, burden of proof, appeals (M29).
- **Elections and campaign finance:** donations, disclosure, conflicts of interest (M32).
- **Diplomacy:** treaties, sanctions and their real costs (M39).
- **Governing shared resources:** quotas and community rules, after Elinor Ostrom (M36).

### Thinking with evidence
- **Cause vs correlation:** every quest's causal chain models how to argue from evidence.
- **Reading charts:** indexed prices, baselines, thresholds (M14, M15).
- **Fact-checking:** claims linked to measurable numbers (player journalism, backlog).
- **Systems thinking:** feedback loops, side effects, unintended consequences (v0.1 results).

### Working with people
- **Collaboration and leadership:** running a guild, organising a group contract (M44).
- **Negotiation:** contract terms, treaties, prices.
- **Communication across cultures:** a global world with English as the common language (M43).
- **Mentoring:** teaching new players, paid by results (backlog).

### Building things
- **Computational thinking:** writing standing orders is a gentle introduction to conditions,
  rules and debugging (M37).
- **Entrepreneurship:** spotting a gap, funding a venture, surviving competition (NPC startups,
  backlog).

## 2. Skills for developers and contributors

| Skill | Where it's practised in this repo |
|---|---|
| Simulation and agent-based modelling | `sim/`, calibration (M9), regions and level of detail (M34) |
| Testing invariants and determinism | `tests/test_invariants.py`, `tests/test_determinism.py`, fuzzing the rule parser (M37) |
| Event sourcing and replay | Persistence, bug reports that replay themselves (M28) |
| Distributed-systems thinking | Transit ledgers and conservation across regions (M34, BLUEPRINT) |
| Privacy engineering | Visibility tiers (M25), privacy as code (M42) |
| Security engineering | Sandboxed rule language (M37), tamper-evident log (M30) |
| Machine learning and reinforcement learning | Agent environment (M24), surrogate models (M40) |
| Data visualisation | Dashboard charts (M14-M15) |
| Economic and game design | Every scenario file is a design experiment; economy CI (M23) |
| CI and developer tooling | GitHub Actions, the economy diff (M23), bisecting bugs (M28) |
| Technical writing | Docs that quote only generated numbers (M22) |
| Open-source collaboration | Issues, reviews, design discussions |

## 3. Development suggestions

**For players (milestone M45, skills passport):**
1. **Skills from verified actions.** The engine already records what players did and why. A
   private skills record notes demonstrated skills ("hedged a harvest with a future before a
   drought: risk management"), each linked to the evidence.
2. **Private by default.** The passport is player-tier (M25). The player chooses whether to share
   it, for example as a signed, non-transferable credential for a CV or a teacher. It can't be
   sold or traded (see [BLOCKCHAIN.md](BLOCKCHAIN.md)).
3. **"Learn more" links.** Each skill links to its lesson (M26) and to one outside resource.
4. **Teacher view.** A class can share passports with a teacher, with consent, and the teacher
   sees which concepts the class has met in play.
5. **No grind.** Skills come from meaningful decisions, not repetition; repeating the same action
   doesn't add more.

**For contributors:**
1. **Tag issues with skills.** Each task in [BUILD_GUIDE.md](BUILD_GUIDE.md) can carry labels such
   as `skill:testing`, `skill:privacy` or `skill:economics`, so people can pick work by what they
   want to learn.
2. **Learning paths.** Short routes through the codebase: "learn event sourcing" (persistence →
   M28 → M30), "learn privacy engineering" (M25 → M42), "learn reinforcement learning" (M24 →
   M40).
3. **Walkthrough docs.** One page per subsystem explaining a single tick of it, with a diagram.
4. **Mentoring.** Experienced contributors review first pull requests within a set time and pair
   with newcomers on their first milestone task.
5. **Recognition.** Contributors are credited in the changelog and AUTHORS; research use is
   cited via CITATION.cff.
6. **University and school partnerships.** Scenarios and lessons as course material; student
   projects built on backlog items; research collaborations with an ethics review.

## 4. Skill tracks

**In scope (chosen 2026-10-21, milestone M47):** T1 Economics, T3 Investing and financial markets,
T5 Politics and governance, T6 Law, T7 International relations, T8 Public policy, T11 Leadership
and project management, T12 Supply chains and operations, T13 Data literacy and statistics, T14
Media literacy and research, T16 Behavioural economics and psychology.

**Not scheduled (open for contributors to propose):** T2 Personal finance, T4 Accounting and
auditing, T9 Entrepreneurship and management, T10 Negotiation and sales, T15 Sustainability and
environmental economics.

A **skill track** is a real-world subject the game teaches through play. Each track lists the
real concepts a player learns, the game mechanics that teach them, where the skill is used in real
life, and which milestones it builds on. The skill scenarios in §5 are example challenges inside
these tracks.

### Money

| Track | Real concepts learned | How the game teaches it | Used in real life for | Builds on |
|---|---|---|---|---|
| **T1 Economics** | Supply and demand, elasticity, inflation, trade, comparative advantage, market failure | Shocks move prices; regions specialise and trade; shortages, monopolies and externalities happen in front of you | Understanding the news, policy, business, voting | v0.1, M20, M34 |
| **T2 Personal finance** | Budgeting, saving, interest, credit scores, debt traps, insurance | Your character's wallet, loans and repayment schedules, credit score, shock insurance | Managing your own money | M17, insurance |
| **T3 Investing and financial markets** | Risk and return, diversification, futures and hedging, speculation, bubbles and crashes | Futures market, guild shares in NPC startups, prediction markets | Pensions, investing, careers in finance | M18, startups |
| **T4 Accounting and auditing** | Double-entry bookkeeping, balance sheets, cash flow, fraud detection | The ledger itself is double-entry; guild books; audit quests catch embezzling treasurers | Running any organisation, business careers | v0.1 ledger, audit quests |

### Society

| Track | Real concepts learned | How the game teaches it | Used in real life for | Builds on |
|---|---|---|---|---|
| **T5 Politics and governance** | Elections, coalitions, lobbying, campaign finance, separation of powers, constitutions | Mayors, guild votes, the campaign-finance register, constitution files | Citizenship, community organising, public service | M32, constitution file |
| **T6 Law** | Contracts, breach and damages, evidence, due process, property rights, precedent | Contract terms, the court system, land registry, case law in the wiki | Signing contracts, renting, employment, disputes | M29, land registry |
| **T7 International relations** | Diplomacy, treaties, sanctions, embargoes, alliances, migration | Regions negotiate, sanction and trade; embargoes create smuggling; people migrate | Understanding world events, diplomacy and NGO careers | M39, migration |
| **T8 Public policy** | Cost-benefit analysis, unintended consequences, policy evaluation, evidence-based policy | Referendum previews, the economy diff, UBI vs relief experiments, price controls | Civil service, think tanks, local government | M23, policy ideas |

### Work

| Track | Real concepts learned | How the game teaches it | Used in real life for | Builds on |
|---|---|---|---|---|
| **T9 Entrepreneurship and management** | Business models, pricing, unit economics, competition, hiring | Starting a workshop, NPC startups, competing with NPC corporations | Starting or running a business | M17, startups |
| **T10 Negotiation and sales** | Interests vs positions, your best alternative to a deal, anchoring, win-win deals | Contract terms, treaties, trading with players in other languages | Job offers, buying a car or home, any sales role | M29, M39, M43 |
| **T11 Leadership and project management** | Planning, delegation, motivation, fair pay, running meetings | Group contracts, guild leadership, councils | Leading teams at work, school or in clubs | M44, guilds |
| **T12 Supply chains and operations** | Logistics, bottlenecks, inventory, resilience, just-in-time vs buffers | Transport, regional trade, roads, disruptions | Operations, retail, manufacturing careers | M34, M35 |

### Mind and world

| Track | Real concepts learned | How the game teaches it | Used in real life for | Builds on |
|---|---|---|---|---|
| **T13 Data literacy and statistics** | Reading charts, baselines, correlation vs causation, probability, forecasting | Causal chains, indexed charts, forecasts scored for accuracy, verifiable claims | Every modern job; judging claims and statistics | v0.1, M14, forecasts |
| **T14 Media literacy and research** | Sources, verification, misinformation, propaganda | Player journalism with fact checks, rumours and imperfect information | Spotting misinformation, journalism and communications careers | Player journalism, rumours |
| **T15 Sustainability and environmental economics** | Renewable resources, the tragedy of the commons, externalities, pollution taxes | Ecology, fisheries and forests, pollution affecting farms | Climate and environmental policy, sustainable business | M36, pollution |
| **T16 Behavioural economics and psychology** | Biases, herd behaviour, panics, trust, incentives, nudges | Bank runs, bubbles, rumours, how players and NPCs respond to incentives | Personal decisions, marketing, policy design | Bank runs, rumours, M44 |

**Already covered elsewhere:** English as a common language (M43), computational thinking through
standing orders (M37), and history through seasonal worlds and historical shock packs.

## 5. Skill scenarios (example challenges, not yet scheduled)

A **skill scenario** is a short, replayable challenge built on a normal scenario file. Each one
has:
- a brief;
- a role for the player;
- a goal the engine measures;
- a time limit;
- a debrief comparing what happened with a real-world case;
- a skills-passport entry (M45) when completed.

Groups of players can take them together. Each works in the fantasy and sci-fi skins (M33).

"Needs" lists the milestones a scenario depends on. Effort is for the scenario itself, once those
exist and the shared framework (about 4 h) is built.

### Money and markets

| # | Scenario | You are... | Goal the engine measures | Skill | Real-world parallel | Needs | Effort |
|---|---|---|---|---|---|---|---|
| S1 | **The Harvest Hedge** | Head of a farming co-op; a drought is forecast with 60% probability | Keep members' income within 20% of normal across the season | Risk management, hedging | Farmers selling crops forward before harvest | M18 | 3 h |
| S2 | **The Bank Run** | Treasurer of a guild bank when a rumour starts | Keep the bank open without the central bank, or with the least emergency borrowing | Liquidity, trust, lender of last resort | Northern Rock (2007), Silicon Valley Bank (2023) | M17, M20, guild banks | 4 h |
| S3 | **Startup Season** | A new workshop owner with a 300-coin loan | Break even within 60 days and repay on time | Business planning, pricing, cash flow | A small-business loan and first-year survival | M17 | 3 h |
| S4 | **The Inflation Desk** | A member of the central bank's board during a supply shock | Keep inflation inside its band without pushing hunger up | Monetary policy, trade-offs | Central banks after the 1970s oil shocks | M20 | 3 h |

### Law and civics

| # | Scenario | You are... | Goal the engine measures | Skill | Real-world parallel | Needs | Effort |
|---|---|---|---|---|---|---|---|
| S5 | **Small Claims Day** | A magistrate (or one side's advocate) with five disputes | Rulings that match the verified evidence; appeals upheld | Contract law, weighing evidence | A small-claims court session | M29 | 3 h |
| S6 | **The Campaign Trail** | A mayoral candidate under contribution limits | Win, or lose with a measurably better platform, with a clean finance register | Campaigning, ethics, policy from data | Election finance rules and disclosure | M32 | 4 h |
| S7 | **The Commons Council** | Chair of a council whose fishery is collapsing | Stock above half capacity after a year, with rules most members voted for | Governing shared resources, consensus | Community-run fisheries in Elinor Ostrom's research | M36 | 3 h |
| S8 | **The Embargo Talks** | A negotiator for one of two regions in a trade war | A treaty both sides ratify, with smuggling and losses measurably lower | Negotiation, knowing your best alternative | Trade negotiations; Fisher and Ury's *Getting to Yes* | M39 | 4 h |

### People and communication

| # | Scenario | You are... | Goal the engine measures | Skill | Real-world parallel | Needs | Effort |
|---|---|---|---|---|---|---|---|
| S9 | **Caravan Captain** | Leader of a four-player group contract (haul, guard, craft, trade) | Deliver on time, within budget, with fair pay splits | Leadership, delegation, planning | Running a small project team | M44 (group contracts) | 3 h |
| S10 | **Trade Mission Abroad** | A trader closing a deal with a player who speaks a different language | A contract both accept, negotiated in English with learning mode | Cross-cultural communication, English | International business negotiation | M43 | 3 h |
| S11 | **The Newsroom** | A reporter investigating a shortage | Publish an article whose every number passes `verify()`, before rumours spread | Journalism, fact-checking | Data journalism | Player journalism | 3 h |
| S12 | **The Mentor** | A veteran guiding three new players | The new players' impact scores after 30 days | Teaching, giving feedback | Workplace mentoring | M44, M24.1 | 3 h |

### Science, systems and technology

| # | Scenario | You are... | Goal the engine measures | Skill | Real-world parallel | Needs | Effort |
|---|---|---|---|---|---|---|---|
| S13 | **The Detective** | An investigator; part of a shortage's causal chain is hidden | Name the root cause and every step, with the fewest paid investigations | Scientific method, testing hypotheses | Root-cause analysis in engineering and medicine | Fog of cause | 4 h |
| S14 | **Automate It** | A shop owner going on a week's holiday | The shop stays profitable on standing orders alone, within the action budget | Computational thinking, debugging | Writing business rules and automations | M37 | 3 h |
| S15 | **The Forecast Office** | A forecaster for the town | Predictions scored with the Brier score (a standard accuracy measure for probability forecasts) | Probability, calibration | Weather and election forecasting | Forecasts, prediction markets | 4 h |
| S16 | **Supply Chain Rescue** | A logistics planner after a bridge collapse | Restore deliveries fastest with the least spending | Operations, finding bottlenecks | Goldratt's theory of constraints; real supply-chain disruptions | M34, M35 | 4 h |

### The shared framework (about 4 h, built once)

- A `[challenge]` section in scenario files: role, goal metric (a `measure()` key and target),
  time limit, debrief text, and the passport skill it awards.
- `questless challenge <name>` in the CLI and a "Challenges" tab in the dashboard.
- A debrief page generated from the run: what you did, what the engine measured, the real-world
  parallel, and a link to the lesson (M26).
- Replays as proof: a completed challenge is a save file anyone can verify, so results can be
  shared with a teacher or an employer.
