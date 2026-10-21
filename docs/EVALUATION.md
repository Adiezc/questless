# QUESTLESS — Critical Evaluation (planning phase)

Status: pre-implementation evaluation (approved) · 2026-10-21 · Author: Adrian Diez Cuadrado (planning assisted by Claude)

Decisions already made by the creator:

| Decision | Choice |
|---|---|
| Demo access | Local install only (one command) |
| Language | Python |
| Visual style | Game-flavoured dashboard (data UI + light fantasy touches) |
| Plan location | Markdown in this repo |

---

## 1. Strongest aspects

1. **Provenance is the product.** "Why does this quest exist?" turns an invisible system into something a designer can inspect in 10 seconds. Most generators can't answer that question. If the answer is computed from real simulation data, it is the most defensible feature in the project.
2. **Funded contracts link quests to scarcity.** If every reward must be escrowed from a real NPC, guild or town budget, quests can't be spammed, rewards mean something, and "a guild that can't afford it can't post it" can be tested.
3. **The loop can be measured.** Shortage → contract → delivery → production recovery can be shown as a before/after time series. That evidence carries more weight than any screenshot.
4. **It fits real MMO practice.** Live MMOs already run NPC and economy simulations on the server. A deterministic, headless engine with a small Python API matches how a studio would prototype a system before porting it.
5. **The scope is honest.** No LLMs in the loop and no 3D. Rule-based agents mean the whole thing is reproducible, testable and fast.

## 2. The five biggest risks

| # | Risk | Why it matters | Mitigation |
|---|---|---|---|
| 1 | **Economy calibration eats the schedule.** | Small economies either collapse (everyone broke or starving) or saturate (nothing is ever short, so no quests). Tuning typically takes 2–4× longer than writing the code. | A closed money loop, target stock levels, clamped prices, a dedicated 1.5 h calibration milestone, and invariant tests that fail loudly on drift. Baseline goal: a *stable* world that produces few quests, so shocks visibly produce more. |
| 2 | **"Causal" becomes cosmetic.** | If provenance is template text stuck onto a trigger, a technical reviewer will spot it within a minute and the core claim fails. | Provenance is built only from recorded evidence (metric, value, threshold, tick). A **counterfactual test** proves it: same seed without the shock → no such contract. |
| 3 | **The player loop is trivial or exploitable.** | "Accept → click Fulfil" with goods appearing from nowhere breaks resource conservation and makes the player meaningless. | The player must *source* goods: buy at market (which moves prices) or import via a caravan (costs coin and days, logged as an external import). Rewards come only from escrow. |
| 4 | **"100 autonomous NPCs" is mostly spectacle.** | With 5 professions and identical rules, 100 agents behave like 5 agents multiplied. Reviewers notice homogeneity. | Seeded per-NPC traits (skill, thrift, stock target, guild loyalty) and per-NPC escalation thresholds. Present them honestly as *rule-based agents*. The impressive part is the contract engine, not the headcount. |
| 5 | **Scope versus 12–20 hours.** | Engine + 4 scenarios + guilds + UI + experiments + README + case study + video is closer to 30 h. | The 2-day target is **engine + 2 scenarios + dashboard + tests + README**. The video, polished case study and scenarios C/D are stretch goals or day 3. A cut list is fixed in advance (see PLAN §E). |

Smaller risks:
- **Streamlit's rerun model** re-executes the script on every click, so world state must live in `st.session_state`, and there is a ceiling on how custom the UI can look.
- **The novelty claim.** Quests from NPC needs have been done before (see §6). Claim the *combination*, not the idea.
- **Environment.** This Mac's Python is 3.9.6. Streamlit requires ≥ 3.10 and `tomllib` requires 3.11. Setup installs Python 3.12 via `uv`.

## 3. Simplest viable architecture

One Python package, two front doors (Python API + Streamlit), no server, no database.

```
            ┌───────────────────────── questless (pip package, pure Python, no UI imports) ─────────────────────────┐
scenario    │  sim/                         contracts/                       api.py                                │
.toml  ───► │  World ─ NPCs ─ Guilds ─►     NeedTracker ─► Detectors ─►       Simulation facade                     │
seed        │  Market ─ Ledger ─ Shocks     Validator ─► ContractBoard        step() accept() fulfil() shock()      │
            │        ▲                      Provenance (evidence records)     snapshot() save() load() replay()     │
            │        └──── consequences ◄────────┘                                                                   │
            └───────────────────────────────────────────────▲──────────────────────────────▲──────────────────────────┘
                                                            │                              │
                                              app/ Streamlit dashboard          cli.py + experiments/ (headless, CSV/JSON)
```

- **Rejected:** Mesa (its scheduler and grid aren't needed for a fixed tick order, and Mesa 4 is in active development, so its API will change), SimPy (this is discrete daily ticks, not event-driven), NetworkX (provenance chains have 3–8 nodes), SQLite (JSON snapshots plus an action log cover persistence and replay), FastAPI (the HTTP layer is postponed).
- **Dependencies:** `streamlit` (Apache-2.0), `plotly` (MIT), `pytest` (MIT, dev), `ruff` (MIT, dev). The engine depends only on the standard library.

## 4. Exact MVP scope (12–20 h)

**In:**
- 1 settlement, 3 sites (Market, Mine, Farms) · 100 NPCs · 5 professions (Farmer, Miner, Blacksmith, Merchant, Guard)
- 4 goods (food, iron_ore, tools, weapons) + coin · 3 guilds (Miners, Merchants, Blacksmiths) + Town Treasury
- Production, consumption, tool wear, hunger · market clearing with dynamic prices · aggregate transport capacity
- Need tracking → 3 contract types (Procurement, Transport, Guild Emergency Supply) with escrow, dedup, cooldown, caps
- Evidence-based provenance + "quest lineage" (contract → consequence → follow-up contract)
- Player: wallet, accept / source / deliver / abandon, guild reputation
- Shocks: mine collapse, drought, (stretch) new deposit, (stretch) guild rivalry
- **Scenario A (iron shortage) and B (drought): fully working and reproducible**
- Seeded determinism, JSON save/load, replay from seed + action log
- Streamlit dashboard · ≥ 10 automated tests incl. invariants · 1 baseline-vs-shock experiment · README + docs + licence files

**Out (explicitly):** HTTP API, multiple settlements, NPC relationships, negotiation, LLMs, hosted deploy, engine integrations, combat.

## 5. What would impress a game studio

Ranked by how a technical designer or lead engineer actually judges a portfolio repo:

1. **Invariants that pass.** "Coin and goods are conserved every tick; 0 invalid contracts in 10,000 simulated days." Studios worry most about exploits and inflation.
2. **Determinism.** Same seed + same actions → identical state hash. Live-ops teams need this for bug reproduction.
3. **Provenance backed by data**, plus the counterfactual test.
4. **Designer knobs.** Every threshold, recipe and premium lives in TOML. A designer can tune the system without touching code.
5. **Measured results.** One chart: shortage duration with and without player contracts (and with and without guilds). Also performance figures (ticks/sec at 100 NPCs).
6. **Clean boundaries.** The engine has zero UI imports; the API is small enough to fit on one page. It reads as portable to C#/C++.
7. **Honest docs.** Stated assumptions, known limitations, what it isn't.

Not very impressive on their own: agent count, visual flourish, any use of the word "AI".

## 6. Comparable work (verified sources)

| Work | What it does | Relation to QUESTLESS |
|---|---|---|
| Doran & Parberry, *Emergent Economies for Role Playing Games* ([PDF](https://ianparberry.com/pubs/econ.pdf)) | Agent-based market where prices emerge from agents' bids and asks and their price beliefs. | Closest prior art for the economy layer. QUESTLESS uses a simpler clearing rule but should cite it. |
| BazaarBot, Lars Doucet ([write-up](https://www.gamedeveloper.com/design/bazaarbot-an-open-source-economics-engine), [repo](https://github.com/larsiusprime/bazaarBot)) | Open-source Haxe implementation of the paper above. Ports exist in Java and Raku. | Economy only, no quests. A good reference for price-belief updating. Licence not verified (the repo has a LICENSE.txt). |
| Breault et al., *Let CONAN tell you a story: Procedural quest generation* ([arXiv 1808.06217](https://arxiv.org/pdf/1808.06217)) | NPCs plan toward goals, and steps they can't do themselves become player quests (e.g. a baker needs wheat). | **Closest prior art for the core idea.** CONAN is planning-based without an economy; QUESTLESS is economy-driven with funding constraints and evidence-based provenance. |
| Doran & Parberry, analysis of 750+ MMORPG quests ([PCG 2011](https://ianparberry.com/pubs/pcg2011.pdf)) and server-side quest execution ([2015](https://ianparberry.com/pubs/DoranParberryQuests2015.pdf)) | Quest structure taxonomy driven by NPC motivations; a runtime framework. | Use the taxonomy to name contract types credibly. |
| "Procedural Quest Generation by NPC in MMORPG", Journal of Korea Game Society ([KCI](https://db.koreascholar.com/Article/Detail/268882)) | NPC desire model + resource management decides when to generate quests. | Very close in spirit. Cite it honestly. |
| Kybartas & Bidarra, survey of story generation (IEEE TCIAIG 2017, [PDF](https://pure.tudelft.nl/ws/files/44107261/10021770_Survey.pdf)) | Taxonomy of plot and space generation by degree of automation. | Use it to position QUESTLESS in the case study. |
| Ryan, *Talk of the Town* / *Curating Simulated Storyworlds* ([overview](https://emshort.blog/2019/05/28/curating-simulated-storyworlds-james-ryan-ch-6f/)); *Neighborly* ([CoG 2022](https://www.kmjn.org/publications/Neighborly_CoG22-abstract.html)) | Simulation-first emergent narrative, plus the problem of *curating* what the simulation produced. | Provenance is a form of curation. Cite this as the conceptual lineage. |
| Oblivion's Radiant AI ([GamesBeat](https://gamesbeat.com/dimming-the-radiant-ai-in-oblivion/)) and Ultima Online's ecology ([Raph Koster](https://www.raphkoster.com/?p=46439)) | Commercial attempts at needs-driven NPCs and simulated ecology. Both were scaled back after unpredictable or player-broken results (Koster disputes parts of the popular UO story). | Cautionary tales. They justify the caps, cooldowns, escrow and determinism in this design. |

**Honest novelty statement:** quests from NPC needs (CONAN, KCI paper) and emergent NPC economies (Doran & Parberry, BazaarBot) both exist. QUESTLESS's contribution is the *combination*: an economic simulation where contracts must be **funded** (by individuals or pooled guild treasuries), are **validated** against conservation, deduplication and feasibility rules, and carry **machine-checkable provenance**, packaged as a small deterministic engine with reproducible experiments.

## 7. Initial two-day plan (summary; full version in PLAN §E)

- **Day 1 (~10 h): a headless engine that works.** Setup → data model and ledger → production and needs → market → guilds → contract engine → provenance → player actions, shocks and scenarios. *Exit gate:* `questless run scenarios/iron_shortage.toml` prints funded contracts with evidence chains, and all tests pass.
- **Day 2 (~9 h): make it convincing.** Test consolidation → calibration → Streamlit dashboard → experiment → README, docs and screenshots.

## 8. Recommended scope reductions and changes

1. **Reframe it as a "quest-economy engine for MMO-style worlds"**, not an MMORPG. That sets expectations correctly.
2. **Cut to 4 goods.** No timber, cloth or coal. One production chain (ore → tools/weapons) plus food is enough for every scenario.
3. **Model transport as aggregate capacity**, not pathfinding. Site stockpiles → market, limited by merchant capacity per day.
4. **No real-time play.** Explicit "Advance 1 / 7 / 30 days" buttons keep everything deterministic.
5. **Treat the 60–90 s video and the polished case study as day 3.** A good README with a GIF is the 2-day deliverable.
6. **Make "Guilds on/off" a config flag from day 1.** The comparison experiment is then nearly free, and it is the best evidence that guilds matter.
7. **Ship scenarios C (new deposit) and D (guild rivalry) as configs only if time remains.** D is the first cut.
