# Architecture

QUESTLESS is one Python package with no third-party runtime dependencies, plus two optional front
ends. The engine never imports the UI.

```
                  ┌───────────────── questless (stdlib only) ─────────────────┐
 scenarios/*.toml │ config.py    TOML -> validated, immutable ScenarioConfig  │
  (extends: ...)  │                                                           │
                  │ sim/                                                      │
                  │   ledger.py     every coin and good; conservation check   │
                  │   entities.py   NPC, Guild, Traits, system accounts       │
                  │   world.py      World, genesis, the tick loop, TickStats  │
                  │   behaviour.py  eat, maintain, produce/craft, wear        │
                  │   transport.py  site stockpiles -> market (capacity)      │
                  │   market.py     clearing, budgets, prices, exports        │
                  │   guilds.py     dues, working-capital relief              │
                  │   shocks.py     time-bounded rate modifiers               │
                  │   alloc.py      deterministic split / allocate / ration   │
                  │   rng.py        named seeded streams                      │
                  │ contracts/                                                │
                  │   needs.py      scarcity streaks (vs poverty)             │
                  │   engine.py     candidates, funding, escrow, lifecycle    │
                  │   validation.py feasibility, board invariants             │
                  │   causes.py     causal walk to root causes, lineage       │
                  │   provenance.py Evidence, metric registry, verify()       │
                  │   model.py      Contract, kinds, statuses                 │
                  │ player.py       logged actions (accept/buy/caravan/...)   │
                  │ persistence.py  save / load / replay + state hash check   │
                  │ metrics.py      time series for UIs and experiments       │
                  │ api.py          Simulation facade (the public API)        │
                  │ cli.py          questless run | replay | demo             │
                  └──────────────▲─────────────────────────────▲──────────────┘
                                 │                             │
                app/ (Streamlit + Plotly, "demo" extra)   experiments/ (matplotlib, "experiments" extra)
```

## The tick

`World.step()` runs one day in a fixed order:

1. **NPC days** (in id order): eat, replace broken equipment, produce or craft, wear. Shortfalls
   are recorded on the NPC's `DailyRecord`.
2. **Transport:** off-market output moves from `npc@site` to `npc`, limited by merchant capacity.
   Haulage fees are pooled and split.
3. **Town:** the upkeep levy on idle coin, then guard wages.
4. **Guild relief:** members who can't afford to keep working are topped up, before the market
   opens.
5. **Market:** each good clears. Unfilled demand (scarcity) and unaffordable demand (poverty) are
   recorded. Prices move. Outside traders buy surplus with coin from earlier caravan sales.
6. **Guild dues** on the day's net gain.
7. **Needs:** scarcity streaks are updated.
8. **Contracts:** expire, withdraw, generate (with provenance), and measure outcomes of delivered
   contracts.
9. **Bookkeeping:** stats are recorded, the day advances, caravans due today unload, and the
   invariants are checked: the ledger conserves everything, the clearing account is empty, and
   escrow equals live rewards.

Player actions happen *between* ticks through `player.apply_action`, which appends to the action
log. Replay re-applies the log at the same ticks, which is what makes save files tiny and exact.

## Key design decisions

| Decision | Why |
|---|---|
| One ledger owns all holdings; NPCs hold no balances | Conservation is a single check, not a property of every module |
| Integer coin and goods; fractional production carried per NPC | No float drift; unbiased rounding |
| Named RNG streams (`genesis.traits`, `market`, `transport`, ...) | Adding a random draw in one system never shifts another's numbers |
| Seeded tie-breaks in every apportionment | An id tie-break silently bankrupted all but one smith (found during calibration) |
| Equal rationing for buyers in a shortage | Pro-rata by bid size compounded wealth into monopoly |
| Scarcity (could pay, no supply) separate from poverty | Contracts must answer real shortages, not just "someone is broke" |
| Escrow before posting | An unfunded contract cannot exist, by construction |
| Evidence carries its metric key and tick | `verify()` re-measures it later; the UI can only claim what the data shows |
| Stdlib-only engine; UI and charts as optional extras | Easy to embed, audit, or port to C#/C++ |

## Extending

- **New good or profession:** add it in `ledger.Asset` / `entities.Profession` and in the scenario
  TOML (recipe or output, equipment, wear). The market, needs and contracts pick it up
  generically.
- **New shock type:** add a `ShockEffect`, apply it where the rate is computed, and make the
  causal walk recognise it in `causes.py`.
- **New contract kind:** add a candidate source in `engine._candidates`, a funding rule in
  `_choose_funder`, delivery semantics in `fulfil`, and evidence. The board invariants apply
  unchanged.
- **HTTP API:** wrap `questless.api.Simulation`. Every method already takes and returns plain
  data or dataclasses.
