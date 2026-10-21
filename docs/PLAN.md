# Questless — Project Plan (A–I)

> Emergent quests from living worlds.
> Status: **implemented as v0.1.0** (2026-10-21). This is the original plan, kept for the record; what was actually built, and where it differs, is in [SIMULATION_SPEC.md](SIMULATION_SPEC.md) and [RESULTS.md](RESULTS.md). · Creator: Adrian Diez Cuadrado
> Companion doc: [EVALUATION.md](EVALUATION.md) (risks, prior art, scope rationale)

Contents: [A. Brief](#a-executive-brief) · [B. Architecture](#b-technical-architecture) · [C. Simulation spec](#c-simulation-specification) · [D. Repository](#d-repository-structure) · [E. 2-day plan](#e-two-day-implementation-plan) · [F. Demo design](#f-interactive-demo-design) · [G. Testing](#g-testing-and-validation) · [H. Release](#h-release-and-presentation) · [I. Roadmap](#i-roadmap)

---

## A. Executive brief

**What it is.** Questless is a small, deterministic Python engine. It simulates a settlement of 100 rule-based NPCs who produce, trade and consume goods, and it turns their *unmet economic needs* into funded, validated player contracts. Every contract carries a machine-checked explanation of why it exists.

**Technical novelty.** NPC economies (Doran & Parberry; BazaarBot) and quests generated from NPC needs (CONAN; KCI 2015) both exist already. Questless combines them, with three properties that are uncommon together:
1. **Funded contracts.** Rewards are escrowed from a real NPC, guild or town budget. No budget means no quest.
2. **Validated contracts.** Deduplication, cooldowns, caps, feasibility checks and coin/goods conservation are tested invariants.
3. **Evidence-based provenance.** "Why does this quest exist?" is answered with recorded metrics and thresholds, and a counterfactual run (same seed, no shock) produces no such quest.

**Audience.** MMO and RPG gameplay programmers, technical and systems designers, simulation engineers, and hiring leads looking at portfolios.

**Realistic MVP.** One settlement, 5 professions, 4 goods, 3 guilds, 3 contract types, 2 fully reproducible scenarios (iron shortage, drought), a Streamlit dashboard, ≥ 10 automated tests, and one baseline-vs-shock experiment. It is a research prototype, not a game.

---

## B. Technical architecture

### Stack

| Component | Choice | Why | Licence |
|---|---|---|---|
| Language | Python 3.12 | Your preference. Fast to iterate, strong testing, and `tomllib` is in the standard library. The Mac's system Python 3.9.6 is too old. | PSF |
| Env/packaging | `uv` + `pyproject.toml` | One-command setup (`uv sync`, `uv run`). Installs Python 3.12 without Homebrew. | MIT/Apache-2.0 |
| Engine | stdlib only (`dataclasses`, `random`, `json`, `tomllib`, `hashlib`) | Zero-dependency core is easy to embed, port and audit. | — |
| UI | Streamlit | Fastest path to an interactive Python dashboard. Theming via `config.toml` + CSS for the game flavour. Needs Python ≥ 3.10. | Apache-2.0 |
| Charts / map | Plotly | Interactive time series and a scatter "settlement map". Native in Streamlit. | MIT |
| Tests | pytest | Standard choice. | MIT |
| Lint/format | ruff | One fast tool. | MIT |
| CI | GitHub Actions | Free for public repos. | — |

**Not used, and why:** Mesa (its scheduler and spaces aren't needed, and Mesa 4 is in pre-release, so the API is changing), SimPy (daily ticks, not discrete events), NetworkX (provenance graphs are tiny), SQLite (JSON + action log is enough), FastAPI (HTTP is roadmap). Licences above were checked on PyPI, conda-forge and GitHub metadata on 2026-10-21. Versions get pinned at setup time.

### Diagram

```
                     ┌──────────────────── questless.sim ────────────────────┐
 scenario.toml ─────►│ World(tick, rng)                                      │
 seed                │  ├─ NPCs (profession, inventory, wallet, needs, traits)│
                     │  ├─ Guilds (treasury, stock, members, policy, rep)     │
                     │  ├─ Sites (Market, Mine, Farms) + stockpiles           │
                     │  ├─ Market (prices, clearing, shortage stats)          │
                     │  ├─ Ledger (every coin/good movement, conservation)    │
                     │  └─ Modifiers (shocks: output ×, capacity ×, duration) │
                     └──────────────┬───────────────────────▲─────────────────┘
                        needs/stats │                       │ deliveries, payouts,
                                    ▼                       │ consequences
                     ┌──────────────────── questless.contracts ──────────────┐
                     │ NeedTracker → Detectors → Funding → Validator → Board │
                     │                 └─ Provenance (Evidence records)      │
                     └──────────────┬───────────────────────▲─────────────────┘
                                    ▼                       │
                     ┌──────── questless.api.Simulation (facade) ────────────┐
                     │ new · step · shock · accept · source · deliver ·      │
                     │ abandon · snapshot · save · load · replay · metrics   │
                     └───────┬─────────────────────┬─────────────────┬────────┘
                             ▼                     ▼                 ▼
                     app/ (Streamlit)     questless.cli         experiments/
```

### How the parts interact

- **NPCs** act on rules only, once per tick, in a deterministic order. They never create contracts directly. They emit **needs** (good, quantity, urgency) when they can't satisfy them through the market.
- **Economic state** (prices, stockpiles, unfilled demand) is the evidence store. The `NeedTracker` keeps a rolling window per need key.
- **Guilds** collect dues from members, keep a treasury and a stock, and can *pool* members' needs into a single larger contract they fund.
- **The contract engine** decides whether a persistent need becomes a contract (detectors), who pays (funding), whether it is allowed (validator), and records why (provenance).
- **Player actions** go only through the API and are appended to an **action log** `(tick, action, args)`. A deterministic world plus the log equals replay.
- **Persistence:** `save()` writes a JSON snapshot (state + RNG state + action log). `replay(seed, scenario, log)` recomputes it, and a test asserts that both produce the same state hash.

---

## C. Simulation specification

All numbers below are **initial values**, tuned during calibration (M9) and stored in `scenarios/*.toml`, never hard-coded.

### C.1 Resources and accounts

| Good | Produced by | Consumed by |
|---|---|---|
| `food` | Farmer (Farms) | everyone, 1/day |
| `iron_ore` | Miner (Mine) | Blacksmith (recipe input) |
| `tools` | Blacksmith | Farmer, Miner, Blacksmith (wear) |
| `weapons` | Blacksmith | Guard (wear) |
| `coin` | — (fixed supply) | — |

**Accounts:** each NPC · each guild · `TOWN` (treasury) · `ESCROW` · `PLAYER` · `OUTSIDE` (the world beyond the map, used for player caravans and scenario discoveries).

**Conservation rules:**
- **Coin:** the sum over all accounts, `OUTSIDE` included, is constant every tick.
- **Goods:** for each good, `Δ total = produced − consumed − spoiled + imported − exported`. Every term is a ledger entry.
- No inventory or wallet ever goes negative. Transfers that would do so are rejected and logged.

### C.2 Professions and recipes (initial)

| Profession | Count | Site | Daily rule |
|---|---|---|---|
| Farmer | 34 | Farms | +5 food × skill × weather; tool wear 0.02 |
| Miner | 20 | Mine | +3 iron_ore × skill × mine_mod; tool wear 0.05; output ×0.3 without tools |
| Blacksmith | 12 | Market | up to 2 crafts: 2 ore → 1 tools, or 3 ore → 1 weapons (chooses higher margin); tool wear 0.03 |
| Merchant | 10 | Market | adds 12 units/day of transport capacity (Mine/Farms → Market) and earns a haulage fee |
| Guard | 24 | Market | paid wage by TOWN; weapon wear 0.04; their purchases are the demand sink for weapons |

Population totals 100. Seeded traits per NPC: `skill ∈ [0.8, 1.2]`, `thrift ∈ [0, 1]` (cash reserve target), `stock_days ∈ [2, 5]` (stock target), `patience ∈ [2, 5]` (days before escalating).

**Wear:** each NPC has `tool_condition ∈ [0, 1]`. When it drops below 0.2 they need 1 tool. The same applies to guards and weapons.
**Hunger:** if an NPC can't eat, `hunger += 1` and productivity × 0.5 while hunger > 2. There is no death in the MVP.

### C.3 NPC data model

```python
@dataclass
class NPC:
    id: str  # "npc_042"
    name: str  # seeded name generator
    profession: Profession
    site: SiteId
    guild_id: str | None
    # wallet and inventory are NOT fields: all coin and goods live in the Ledger under the
    # NPC's id (decided in M1), so conservation is checked in one place.
    tool_condition: float
    hunger: int
    traits: Traits  # skill, thrift, stock_days, patience
    state: NPCState  # WORKING | IDLE_NO_INPUT | HUNGRY | WAITING_ON_CONTRACT
    history: deque[DailyRecord]  # last 30 days: produced, consumed, bought, sold, unmet
```

### C.4 Guild data model

```python
@dataclass
class Guild:
    id: str  # "miners" | "merchants" | "blacksmiths"
    name: str
    members: list[str]  # NPC ids
    treasury: int  # coin
    stock: dict[Good, int]
    dues_rate: float  # 0.05 of member income per day
    policy: (
        GuildPolicy  # emergency_threshold, max_contract_share (≤ 0.4 of treasury), reward_premium
    )
    reputation: dict[str, int]  # player_id -> score (−100..100)
    rival: str | None  # stretch: scenario D
```

**Membership:** Miners Guild = miners; Merchants Guild = merchants + farmers (farmers sell through them); Blacksmiths Guild = blacksmiths. Guards belong to no guild and are funded by TOWN, which shows that contracts also arise outside guilds.

**Guild mechanics in the MVP:** (1) membership, (2) treasury from dues, (3) pooled funding of contracts, (4) collective response when ≥ X% of members share a need, (5) player reputation, which scales future rewards ±10% and gates "priority" contracts. Rivalry (6) is scenario D, a stretch goal.

### C.5 Market and prices

One market at the Market site, cleared once per tick per good, at the posted price `p_t`:

1. **Asks:** each holder offers `inventory − stock_target` (if > 0). Producers' output only reaches the market after transport.
2. **Bids:** each buyer requests `stock_target − inventory` (if > 0), capped by `floor((wallet − cash_reserve) / p_t)`.
3. **Fill:** `S = Σ asks`, `D = Σ bids`. If `S ≥ D`, all bids are filled and sellers are filled pro rata. Otherwise asks are filled and bids are filled pro rata. Rounding remainders go in sorted id order, which keeps it deterministic. Trades settle at `p_t`; the market tax (3%) goes to TOWN.
4. **Unfilled demand** `D − filled` is recorded per buyer. This is the main shortage signal.
5. **Price update:** `p_{t+1} = clamp(p_t × (1 + α × (D − S) / max(D + S, 1)), p_min, p_max)` with `α = 0.15` and the clamp at `[0.25, 4] × base_price`.

This is deliberately simpler than the Doran & Parberry belief-based double auction. It is stable, explainable and deterministic. The richer auction is on the roadmap.

**Revised during M3 (implemented):** the pure excess-demand rule above drove prices to the floor or ceiling and caused shortage spirals in 365-day runs. The implemented rule combines a *flow* term (today's consumption vs production) with a damping *stock* term (days of cover vs `target_cover_days`). Gatherers' effort scales with price/base price, which gives an upward-sloping supply curve. Supporting stabilisers:
- producers pause once unsold stock exceeds `max_unsold_days` of recent sales;
- purchases keep a food reserve, and crafters only buy inputs while crafting is profitable;
- haulage fees are a share of goods value, pooled daily;
- a town upkeep levy on idle coin funds guard wages;
- seeded tie-breaks in integer apportionment. An id tie-break had silently bankrupted all but one smith.

Result over seeds 1–5 and 42: no unpaid-wage days, food price variation ≤ 11%, and 4–5 NPCs hungry on average (poverty; guild relief arrives in M4).

**Transport:** production lands in site stockpiles (Mine, Farms). Each tick `shipped = min(stockpile, capacity × capacity_mod)` moves to the producers' market inventories, and the merchants are paid a fee. A backlog above `backlog_threshold` days of output is a transport bottleneck signal.

### C.6 NPC decision logic (rule priority, evaluated each tick)

1. **Eat:** consume 1 food if held. Otherwise mark the need `food`.
2. **Maintain:** if the tool or weapon condition is below threshold, replace it from inventory if possible. Otherwise mark the need `tools` / `weapons`.
3. **Produce:** run the recipe if inputs are present. If not, the state becomes `IDLE_NO_INPUT` and the need is marked as the missing input.
4. **Trade:** post asks and bids (see C.5).
5. **Escalate:** if a need has been unmet for `≥ patience` days *and* the market's unfilled demand for that good is > 0, emit a `Need` to the `NeedTracker` with severity `= unmet_qty × days_unmet`.

NPCs never escalate if the market *could* supply them and they simply can't afford it. That case is recorded as `unaffordable`, which is a separate metric, so poverty doesn't masquerade as scarcity.

### C.7 Contract model

```python
@dataclass
class Contract:
    id: str  # "C-0007", sequential, deterministic
    kind: ContractKind  # PROCUREMENT | TRANSPORT | GUILD_SUPPLY
    requester: AccountRef  # npc_031 | guild:blacksmiths | TOWN
    reason: str  # rendered from provenance, never free text
    objective: Objective  # deliver(good, qty, to_site) | haul(good, qty, from, to)
    reward: int  # coin, escrowed at creation
    rep_reward: int
    created_tick: int
    deadline_tick: int
    status: Status  # OPEN | ACCEPTED | FULFILLED | EXPIRED | CANCELLED
    dedup_key: tuple  # (requester_scope, kind, good)
    provenance: Provenance  # evidence chain, see C.9
    outcome: Outcome | None  # effects measured after resolution
    parent_id: str | None  # quest lineage: contract caused by a previous contract's consequences
```

**Consequences, defined up front:**
- **Fulfilled:** goods move PLAYER → requester, escrow → PLAYER, reputation +, the requester's state is re-evaluated next tick, and the `Outcome` records production 7 days before and after.
- **Expired or abandoned:** escrow refunded to the funder, reputation − (if it was accepted), the need persists, and severity may escalate (an NPC need can become a guild need).

### C.8 Contract-generation algorithm

```
for need_key, need in need_tracker.persistent(min_days=patience):        # sorted, deterministic
    kind      = detector_for(need)          # procurement | transport | guild_supply
    funder    = choose_funder(need)         # NPC if wallet allows, else guild (if member & policy allows), else TOWN (guards only), else NONE
    if funder is NONE:                      record(need, "unfunded");      continue
    if board.has_open(need.dedup_key):      record(need, "duplicate");     continue
    if board.in_cooldown(need.dedup_key):   record(need, "cooldown");      continue
    if board.open_count() >= GLOBAL_CAP:    record(need, "cap_reached");   continue
    qty     = min(need.unmet_qty, feasible_qty(need.good))   # must exist in market, stockpile, or OUTSIDE import
    if qty <= 0:                            record(need, "infeasible");    continue
    reward  = round(qty × price(good) × urgency_premium(need) × rep_mod)
    reward  = min(reward, funder.max_contract_budget())
    if reward < qty × price(good):          record(need, "underfunded");   continue   # a contract must at least cover market cost
    deadline = tick + max(min_travel_days(need) + 2, policy.deadline_days)
    escrow(funder → ESCROW, reward)         # atomic; fails ⇒ no contract
    board.add(Contract(..., provenance = build_provenance(need)))

guild aggregation (runs first): if ≥ emergency_threshold of a guild's members share the same need,
    merge them into ONE GUILD_SUPPLY contract funded from the treasury; member needs are marked "covered".
```

Each "record" outcome is a metric, which feeds the "invalid/suppressed contracts" dashboard counter.

**Cancellation rule:** an OPEN (not accepted) contract is cancelled only if its need has been resolved for 2 consecutive days, and a cooldown (`5 days`) then applies to the key. This prevents create/cancel flapping.

### C.9 Provenance representation

```python
@dataclass(frozen=True)
class Evidence:
    tick: int
    # kind: "production_drop" | "inventory_below_target" | "unfilled_demand" | "price_spike"
    #       | "transport_backlog" | "guild_emergency" | "funding_decision" | "shock"
    kind: str
    subject: str  # "site:mine" | "npc_031" | "market:iron_ore" | "guild:blacksmiths"
    metric: str  # "iron_ore_output_per_day"
    value: float
    threshold: float | None
    baseline: float | None
    caused_by: tuple[int, ...]  # indexes of earlier evidence in the chain → small DAG


@dataclass(frozen=True)
class Provenance:
    chain: tuple[Evidence, ...]  # ordered root cause → contract
    world_hash: str  # hash of the snapshot at creation tick
    parent_contract: str | None
```

The chain is assembled by walking back from the need through recorded stats. Example for scenario A:

1. `shock` · site:mine · output modifier 0.3 (day 10)
2. `production_drop` · site:mine · iron_ore_output 61 → 18/day (baseline 60)
3. `unfilled_demand` · market:iron_ore · 22/day unfilled, 6 consecutive days
4. `inventory_below_target` · 9 of 12 blacksmiths below their ore target
5. `production_drop` · tools output 22 → 4/day
6. `guild_emergency` · guild:blacksmiths · 75% of members affected ≥ 60% threshold
7. `funding_decision` · treasury 1,840 → escrow 520 (28% ≤ 40% cap)

Text is rendered *from* these fields, so the UI can't claim anything the data doesn't show.

### C.10 Tick sequence and main loop

```python
def step(world, n=1):
    for _ in range(n):
        t = world.tick
        world.apply_scheduled(t)  # scenario shocks + player actions from the action log
        world.modifiers.decay(t)  # expire shocks
        # NPCs act in sorted id order (a seeded shuffle is optional and still deterministic)
        for npc in world.npcs_in_order():
            npc.eat(world)
            npc.maintain(world)
            npc.produce(world)
        world.transport.ship(world)  # site stockpiles → market, capped by capacity
        world.town.pay_wages(world)  # TOWN → guards
        world.guilds.collect_dues(world)
        world.market.clear(world)  # asks/bids, fills, tax, unfilled demand
        world.market.update_prices()
        world.needs.update(world)  # NPC escalations, aggregated per key
        world.contracts.expire_and_cancel(world)  # deadlines, resolved needs, refunds, cooldowns
        world.contracts.generate(world)  # algorithm C.8
        world.contracts.measure_outcomes(world)  # before/after; may spawn lineage
        world.metrics.record(world)
        assert_invariants(world)  # on in tests and dev, cheap at 100 NPCs
        world.tick += 1
```

**Safeguards:** a global cap on open contracts (12), a per-requester cap (1 per good), cooldowns, at most 3 new contracts per tick, integer coin, and every loop bounded by entity count (no `while` loops on world state).

### C.11 Player model and actions

- `PLAYER` has a wallet (start 300 coin), an inventory, reputation per guild, and max 3 accepted contracts.
- `accept(contract_id)`: OPEN → ACCEPTED.
- `buy(good, qty)`: buys at the market at the current price. The purchase is a real trade, so it moves price and supply and can worsen the shortage it is meant to solve.
- `caravan(good, qty)`: imports from OUTSIDE at 1.6 × base price and arrives in 3 days. Logged as an import, coin goes to OUTSIDE, and ore/food only (not crafted goods).
- `deliver(contract_id)`: requires the goods in the player's inventory before the deadline, then performs the transfers in C.7.
- `abandon(contract_id)`: refund and a reputation penalty.

**Shocks:** `mine_collapse(mod=0.3, days=20)`, `drought(mod=0.4, days=25)`, *(stretch)* `new_deposit(mod=1.8, +6 miner jobs)`, *(stretch)* `rivalry(guild_a, guild_b, good)`.

---

## D. Repository structure

```
questless/
├── README.md  LICENSE  CITATION.cff  AUTHORS.md  CONTACT.md  CONTRIBUTING.md  CHANGELOG.md
├── pyproject.toml            # package "questless", scripts: questless = questless.cli:main
├── .github/workflows/ci.yml  # ruff + pytest on 3.11/3.12
├── src/questless/
│   ├── __init__.py           # version, public API re-exports
│   ├── api.py                # Simulation facade                         [MVP]
│   ├── config.py             # TOML → typed config, validation           [MVP]
│   ├── sim/
│   │   ├── world.py          # World, tick loop                          [MVP]
│   │   ├── entities.py       # NPC, Guild, Site, Traits, enums           [MVP]
│   │   ├── ledger.py         # accounts, transfers, conservation checks  [MVP]
│   │   ├── behaviour.py      # eat/maintain/produce/escalate rules       [MVP]
│   │   ├── market.py         # clearing + price update                   [MVP]
│   │   ├── transport.py      # aggregate capacity                        [MVP, cut #4]
│   │   ├── guilds.py         # dues, aggregation, policy                 [MVP]
│   │   └── shocks.py         # modifiers                                 [MVP]
│   ├── contracts/
│   │   ├── needs.py          # NeedTracker                               [MVP]
│   │   ├── engine.py         # generation, funding, lifecycle            [MVP]
│   │   ├── validation.py     # dedup, caps, feasibility, cooldown        [MVP]
│   │   └── provenance.py     # Evidence, Provenance, renderer            [MVP]
│   ├── player.py             # player actions                            [MVP]
│   ├── metrics.py            # time series + summary indicators          [MVP]
│   ├── persistence.py        # save/load/replay/state hash               [MVP]
│   └── cli.py                # run / replay / experiment                 [MVP]
├── app/
│   ├── streamlit_app.py      #                                           [MVP]
│   ├── views/                # world, board, provenance, npcs, guilds, economy
│   ├── theme.css  .streamlit/config.toml
├── scenarios/  baseline.toml  iron_shortage.toml  drought.toml  [discovery.toml  rivalry.toml = stretch]
├── experiments/ shock_vs_baseline.py  guilds_on_off.py  results/ (committed CSV + PNG)
├── tests/ unit/  integration/  test_invariants.py  test_economic_justification.py  test_determinism.py
└── docs/ EVALUATION.md  PLAN.md  ARCHITECTURE.md  SIMULATION_SPEC.md  DEMO.md  CASE_STUDY.md  images/
```

**Postponed:** `http/` (FastAPI), `integrations/`, multi-settlement `region/`, `dialogue/` (LLM), Hypothesis property tests, docs site.

---

## E. Two-day implementation plan

Estimated total ≈ 19 h of focused AI-assisted work, plus a 1 h buffer. Tests are written inside each milestone, not at the end.

### Day 1 — headless engine (~10 h)

| # | Milestone | Files | Requirements | Acceptance criteria | Depends | Est. |
|---|---|---|---|---|---|---|
| M0 | Setup | `pyproject.toml`, licence files, CI, `.gitignore` | `uv` + Python 3.12, git init, ruff, pytest, MIT LICENSE, placeholder CONTACT | `uv run pytest` passes (1 smoke test); `uv run ruff check` clean | — | 0.75 h |
| M1 | Data model + ledger | `entities.py`, `ledger.py`, `config.py`, `baseline.toml` | Dataclasses, enums, integer coin, transfer API that rejects negatives, TOML loader | 100 NPCs built from a seed; total coin and goods are identical across two builds; a negative transfer raises | M0 | 1 h |
| M2 | Behaviour + production | `behaviour.py`, `world.py`, `shocks.py` | Eat/maintain/produce, wear, hunger, recipes, modifiers, tick loop skeleton | 30 ticks run; conservation invariant holds every tick; a mine shock reduces ore output by the modifier ±5% | M1 | 2 h |
| M3 | Market + transport | `market.py`, `transport.py` | Clearing, pro-rata fills, tax, price update, unfilled demand, capacity | Excess demand raises the price, excess supply lowers it, clamps hold; coin conserved through trades | M2 | 1.5 h |
| M4 | Guilds | `guilds.py` | Membership, dues, treasury, policy, `guilds_enabled` flag | Dues move coin member → guild; flag off ⇒ no guild accounts are touched | M3 | 1 h |
| M5 | Contract engine | `needs.py`, `engine.py`, `validation.py` | Algorithm C.8, escrow, lifecycle, dedup, cooldown, caps, suppression metrics | Tests T1, T3, T5, T6, T10 pass (see G) | M3, M4 | 2.5 h |
| M6 | Provenance + lineage | `provenance.py` | Evidence collection, chain assembly, text renderer, parent links | Every contract has ≥ 3 evidence items; each evidence value matches the recorded metric for that tick | M5 | 1 h |
| M7 | Player, scenarios, persistence | `player.py`, `persistence.py`, `api.py`, `cli.py`, `iron_shortage.toml`, `drought.toml` | Actions, caravan, action log, save/load, replay, state hash, CLI `run` | `questless run scenarios/iron_shortage.toml` prints contracts and chains; T2 and T8 pass | M6 | 1.5 h |

**Day 1 exit gate:** the CLI shows scenario A and B contracts with provenance, all tests are green, and invariants hold for 365 ticks. **If the gate is missed, Day 2 starts by finishing it. The UI waits.**

### Day 2 — make it convincing (~9 h)

| # | Milestone | Files | Requirements | Acceptance criteria | Depends | Est. |
|---|---|---|---|---|---|---|
| M8 | Test consolidation | `tests/*` | Fill gaps: T4 counterfactual, T7 invariants, T9, determinism across save/load | ≥ 10 tests green in < 10 s | M7 | 1 h |
| M9 | Calibration | `scenarios/*.toml`, `experiments/` | Tune so that baseline is stable (≤ 1 contract/week, prices within ±25%) and shocks produce contracts within 5–10 days, with recovery after fulfilment | Baseline 365 days: no starvation spiral, coin Gini stable; A and B meet the targets in G.3 | M8 | 1.5 h |
| M10 | Dashboard | `app/*` | Layout F, theme, quest board, provenance viewer, inspectors, shocks, time controls, before/after panel | A new user can run the 2-minute script in F.3 without help; no full-page error on any click | M7 (M9 for good data) | 3 h |
| M11 | Experiments | `experiments/*`, `results/` | Baseline vs shock (with and without player fulfilment); guilds on/off; 10 seeds each | CSV + 2 PNG charts committed; numbers quoted in README | M9 | 1 h |
| M12 | Docs + release prep | README, `ARCHITECTURE.md`, `SIMULATION_SPEC.md`, `DEMO.md`, CITATION.cff, CONTRIBUTING.md, screenshots, GIF | See H | Fresh clone → `uv run questless demo` works by following only the README | M10, M11 | 1.5 h |

**Critical path:** M1 → M2 → M3 → M5 → M6 → M7 → M10 → M12. M4 (guilds) can slip into M5 if needed. M9 calibration is the most likely place to overrun.

**Cut order if behind** (first cut first):
1. Scenarios C and D (already stretch)
2. Guilds on/off experiment (keep the flag)
3. Settlement map visual (tables are enough)
4. Transport contracts and capacity (drought becomes procurement-only)
5. JSON save/load (keep seed + action-log replay)
6. GIF (screenshots only)

**Never cut:** conservation invariants, escrow funding, provenance evidence, determinism, the counterfactual test.

**Day 3 (optional, ~4 h):** 60–90 s video, CASE_STUDY.md, scenarios C and D.

---

## F. Interactive demo design

### F.1 Layout (Streamlit, wide mode)

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ ⚔ Questless   Scenario [Iron Shortage ▾]  Seed [42]   Day 23   ▶ +1  ▶▶ +7  ⏩ +30  ↺ Reset │
│ Shocks: [⛏ Mine collapse] [☀ Drought] [💎 New deposit]   Player: 412 coin · Rep ⛏+10 ⚒+25 │
├──────────────────────────┬────────────────────────────────────┬──────────────────────────┤
│ LIVING WORLD             │ QUEST BOARD (parchment cards)      │ WHY DOES THIS QUEST EXIST?│
│ Settlement map (Plotly): │ ┌──────────────────────────────┐   │ C-0007 · Blacksmiths ⚒   │
│  Mine · Farms · Market   │ │ ⚒ Ore for the Forges   URGENT│   │ ● Day 10 Mine collapse   │
│  NPC dots by profession, │ │ 40 iron ore → Market         │   │ │ output ×0.3             │
│  grey = idle/no input    │ │ 520 coin · 6 days left       │   │ ● Ore output 61 → 18/day │
│ Price sparklines (4)     │ │ [Why?] [Accept]              │   │ ● 22/day unfilled demand │
│ Health KPIs:             │ └──────────────────────────────┘   │ ● 9/12 smiths below stock│
│  idle NPCs · shortages · │ suppressed: 3 duplicate, 1 unfunded│ ● Tools 22 → 4/day       │
│  open contracts          │                                    │ ● Guild emergency 75%    │
│                          │                                    │ ● Escrow 520 of 1,840    │
│                          │                                    │ [mini chart: evidence    │
│                          │                                    │  metric + threshold line]│
├──────────────────────────┴────────────────────────────────────┴──────────────────────────┤
│ Tabs: Economy (prices, output, stock) · NPCs (table → inspector) · Guilds · Event log · Experiment │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

**Game flavour, kept light:** a parchment-coloured card surface, a guild crest glyph per requester, a serif display font for headings only, and a dark slate background. Charts and tables stay clean and readable. The `high-end-visual-design` and `design-taste-frontend` skills are applied at M10.

### F.2 Interactions

- **Time:** +1 / +7 / +30 days. A "Run until next contract" button keeps the demo fast.
- **Inspect:** click an NPC or guild → drawer with inventory, wallet, state, 30-day history and open needs.
- **Quest board:** filter by kind and guild. Each card has *Why?* (opens provenance) and *Accept*.
- **Fulfil flow:** after Accept, the card shows the sourcing options *Buy at market (price, impact warning)* or *Send caravan (3 days)*, then *Deliver*.
- **Consequence panel:** after delivery, a before/after strip ("Smithy output 4 → 19 tools/day over 5 days; ore price 41 → 27"), and any follow-up contracts are shown as children in the lineage.
- **Shocks:** one click applies a shock at the current day. It is logged and replayable.
- **Reproducibility:** "Copy replay" exports seed + scenario + action log as JSON.

### F.3 The 30-second and 2-minute scripts

- **30 s:** the app opens on Iron Shortage at day 20 with a contract already on the board and the provenance panel open. The headline reads: *"This quest exists because the mine collapsed 10 days ago. Every line below is measured."*
- **2 min:** click *Why?* → read the chain → Accept → Buy ore (price jumps) or caravan → +3 days → Deliver → watch tools output recover → switch the scenario to Drought → apply a shock → +7 days → new transport and supply contracts appear.

---

## G. Testing and validation

### G.1 Economic-justification tests (the core claims)

| ID | Test | Asserts |
|---|---|---|
| T1 | Iron shortage → procurement | After the mine shock, within ≤ 10 days a PROCUREMENT or GUILD_SUPPLY contract for `iron_ore` exists, funded by the Blacksmiths Guild or a smith; its provenance contains `production_drop(site:mine)` and `unfilled_demand(market:iron_ore)` |
| T2 | Completion changes the world | Delivering: requester ore +qty exactly, player coin +reward exactly, escrow −reward; blacksmith tools output in the following 5 days > the 5 days before |
| T3 | No unfunded contracts | With the guild treasury set below the minimum and smith wallets empty, the need is recorded as `unfunded` and no contract is created |
| T4 | Counterfactual | Same seed, same days, no shock ⇒ no `iron_ore` contracts |
| T5 | Deduplication | A persistent shortage over 30 days ⇒ at most 1 open contract per dedup key at any tick |
| T6 | No flapping | A need oscillating around its threshold does not create/cancel more than once per cooldown window |

### G.2 Unit, integration and invariant tests

- **Unit:** ledger transfers, price update and clamps, pro-rata fill rounding, recipe production, wear, need persistence windows, reward formula, deadline formula, provenance renderer.
- **Integration:** a full scenario A run; a full scenario B run; save at day 15 → load → continue == uninterrupted run; replay(seed, log) == live run.
- **Invariants (checked every tick in the test suite):** T7 coin and goods conservation · T9 no negative balances · T10 open contracts ≤ cap even under combined shocks · every contract has escrow == reward while OPEN/ACCEPTED · every contract has a non-empty provenance whose evidence matches the metrics store · no contract for a good with zero feasible supply.
- **Determinism (T8):** two runs with the same seed and log give the same SHA-256 state hash at day 100.
- **Performance:** 365 days × 100 NPCs in < 2 s on the M4 (logged, not a hard failure).

### G.3 Measured indicators (`metrics.py`, shown in the dashboard and experiments)

| Indicator | Definition | Target / use |
|---|---|---|
| Contracts generated / fulfilled / expired | counts per kind | Baseline ≤ 1/week; shock ≥ 3 in 15 days |
| Invalid contracts | contracts violating any invariant | **0** (hard requirement) |
| Suppressed needs | by reason: duplicate, unfunded, cooldown, cap, infeasible | Shows the safeguards working |
| Shortage duration | days with unfilled demand > 10% for a good | Shorter with player fulfilment than without |
| Guild treasury change | Δ per guild over the run | Explains funding behaviour |
| Production recovery | days until output returns to ≥ 90% of baseline after the shock ends | Compare: no player vs player fulfils |
| Idle NPC-days | NPC-days in `IDLE_NO_INPUT` | Human-readable impact |
| Price volatility | stdev / mean per good | Baseline stability check |
| Runtime | ms per tick | Performance claim |

### G.3b Calibration results (M9, implemented)

Run `uv run python experiments/calibrate.py` (10 seeds, 120 days); the output is saved in `experiments/results/calibration.txt`.

| Scenario | First contract after shock | Recovers after shock ends | Avg hungry NPCs |
|---|---|---|---|
| Baseline | 0–1 contracts / 120 days | n/a | 1.1 |
| Iron shortage (ore x0.2, 30 days) | 10–14 days | 10/10 seeds, median 19.5 days | 0.0 |
| Mine disaster (ore x0.1, 40 days) | 10–13 days | 0/10 (economic trap) | 7.4 |
| Drought (food x0.4, 25 days) | 6–8 days | 10/10, 1 day | 4.6 |
| Bandits (transport x0.3, 20 days) | 6–7 days | 10/10, 3 days | 7.6 |

Changes made during calibration:
- **Equal rationing.** Buyers in a shortage get equal shares, not shares proportional to their bids, which had let one smith take all the ore and bankrupt the rest.
- **Working-capital relief.** Guild relief covers a replacement tool and one craft's inputs, not only food.
- **Imports of crafted goods.** Caravans can bring tools and weapons, so a tools shortage becomes a quest the player can complete.
- **Pooling among users only.** Emergency shares are counted among members who use the good.
- **Minimum reward of 60.** Single-unit jobs are left to pooled contracts.
- **Reputation.** Guild rewards move by up to ±10% with the player's reputation.

The mine-disaster trap is a finding, not a bug: broke miners cannot afford tools, and without tools they cannot mine. M11 tests whether player contracts get the economy out of it.

### G.4 Reproducible demonstration experiment

`uv run python experiments/shock_vs_baseline.py --seeds 10` runs four arms over 120 days: **baseline**, **shock, no player**, **shock + scripted player** (accepts and fulfils every feasible contract), and **shock + player, guilds off**. It outputs `results/summary.csv` plus two charts: ore and tools output over time with the shock window shaded, and shortage duration per arm with seed spread. The README quotes the medians.

---

## H. Release and presentation

**v0.1.0 checklist**
- `LICENSE`: MIT, `Copyright (c) 2026 Adrian Diez Cuadrado`.
- Source headers: `# SPDX-License-Identifier: MIT` + `# Copyright (c) 2026 Adrian Diez Cuadrado` in each module.
- `AUTHORS.md`: Adrian Diez Cuadrado (creator, original concept and design). Contributors are listed via git history.
- `CITATION.cff`: cff-version 1.2.0, title, authors (family-names: Diez Cuadrado, given-names: Adrian), version, date-released, licence MIT, repository-code `{{GITHUB_REPO_URL}}`.
- `CONTACT.md`: "Studios interested in collaboration, integration, consulting or employment:" with `{{EMAIL}}`, `{{LINKEDIN_URL}}`, `{{GITHUB_PROFILE}}`. Placeholders only until you supply them.
- `CONTRIBUTING.md`: setup, run tests, style (ruff), PR checklist (invariant tests must pass), scope guidance.
- **Licensing language (accurate):** MIT allows use, modification, distribution and commercial use, provided the copyright and permission notice is included in copies or substantial portions of the software. The README *politely requests* (does not require) a credit or a heads-up if a studio uses it.

**README structure:** title + tagline → GIF (provenance click-through) → "What is this?" (3 sentences) → "Why does this quest exist?" screenshot → Quickstart (3 commands) → How it works (diagram + loop) → Results (experiment chart + numbers) → Use the engine from Python (10-line example) → Design guarantees (invariants list) → Limitations → Prior art and citations → Roadmap → Creator & contact → Licence.

**Quickstart (target):**
```bash
git clone {{GITHUB_REPO_URL}} && cd questless
uv sync
uv run questless demo
```

**Demo deployment:** local only, as decided. A hosted version (Streamlit Community Cloud) is a 1-hour roadmap item if wanted later.

**Media:** screenshots via macOS ⌘⇧5; GIF made from a screen recording with `ffmpeg` (a local tool, not a dependency). The 60–90 s video is Day 3: hook (5 s) → shock (10 s) → provenance (25 s) → fulfil + recovery (25 s) → experiment chart + repo/contact (15 s).

**Case study (`CASE_STUDY.md`, Day 3):** problem → prior art → design (funded, validated, explained) → results → what failed during calibration and why → next steps. About 1,200 words.

**GitHub topics:** `game-ai`, `procedural-generation`, `agent-based-modeling`, `game-economy`, `mmorpg`, `simulation`, `quest-generation`.

---

## I. Roadmap

> Superseded for the next release by [ROADMAP.md](ROADMAP.md) (v0.2 build path: fixes, intuitive UI, relief and loans, futures, smuggling, run reports).

| Horizon | Feature | Notes |
|---|---|---|
| **2 days (this plan)** | Engine, 2 scenarios, dashboard, tests, experiment, README | — |
| **+1 day** | Scenarios C (discovery) and D (guild rivalry), video, case study, optional hosted demo | Configs + 1 detector each |
| **1–2 weeks** | HTTP/JSON API (FastAPI) · Doran & Parberry belief-based auction · NPC memory (who helped me) · richer guild policy (loans, rivalry bidding) · contract chains as planned multi-step quests | Engine API is already the boundary |
| **1–2 months** | Multi-settlement trade + caravan routes · regional price differences → arbitrage/escort contracts · player-run businesses · NPC negotiation over rewards · scenario editor UI · property-based tests | Needs a spatial layer and performance work |
| **3+ months** | Unity/Godot/Unreal integration via the HTTP API or a C# port · multiplayer persistent world (contract contention, reservations) · LLM dialogue that *reads* provenance (no LLM in the decision loop) · large-scale runs (10k NPCs, numpy/Rust core) | Production-grade work |

---

## Approval needed

Reply with one of:
1. **"Approved"**: I start M0 (setup: `uv`, Python 3.12, git init, licence files).
2. **"Approved with changes: …"**: e.g. different professions, different scenarios, a different UI framework.
3. Questions about any section.
