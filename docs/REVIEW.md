# Review: stress tests, UX audit and feature ideas (2026-10-21, v0.1.0)

How this was tested:
- **Engine:** 19 extreme configurations, 150 fuzzed configs (60 valid, all run), API abuse
  cases, a 2,000-day run, 1,000 NPCs, and a 365-day save/load. Invariants (conservation,
  escrow, caps, no duplicate contracts) were checked on every simulated day.
- **Dashboard:** Streamlit's headless test harness, driven to day 360 in two scenarios, plus a
  visual review in the browser at 1280 and 1440 px.

## 1. What holds up

- **No crashes from valid input.** That covers degenerate worlds (no merchants, no farmers, a
  single NPC), extreme shocks (everything ×0 forever, ×10 booms, 50 stacked shocks), broke
  treasuries, no outside stock, and 60 randomly perturbed configs.
- **Invariants never failed** on any day of any run.
- **Speed:**

  | Scale | Time per simulated day |
  |---|---|
  | 100 NPCs | 1.5 ms |
  | 500 NPCs | 7 ms |
  | 1,000 NPCs | 14 ms |

  Linear scaling. A 2,000-day run takes 3 s.
- **Saves:** a 365-day save is 9 KB and replays in 0.6 s with a matching state hash.
- **Dashboard:** reruns take 110-150 ms at day 360, with 0 exceptions across 30+ interactions.

## 2. Where it breaks

| # | Finding | Severity | Fix |
|---|---|---|---|
| B1 | **A NaN or infinite shock factor is accepted, then crashes the world on every later tick.** This works through `sim.shock(...)` *and* through TOML (`factor = nan`), because NaN fails every `<` check. | **Bug, high** | Reject non-finite numbers in `config._number` and in `player.shock`. Add a test. |
| B2 | **Guild treasury card and chart disagree** (551 vs ~910 coin on the same day). `TickStats.guilds` is recorded before the day's contract escrow is taken. | Bug, medium | Record treasuries after contracts run, or show "available + in escrow". |
| B3 | **The quest board empties during the worst crisis.** In Mine Disaster at day 149, demand that buyers can pay for and can't get is 0, but demand they *can't afford* is 95 ore and 30 tools. Poverty never produces contracts, by design, so the board says "No open contracts". | Design gap, high | Show a "Why no quests?" panel, and add relief or loan contracts (feature F2). |
| B4 | **The economy doesn't scale with population.** At 5× and 10× NPCs, average hunger is 37 and 93 (vs 0.7). Town, guild and player money are absolute amounts, not per head. | Design gap, medium | Express treasuries and outside stock per member, per guard and per NPC in the config. |
| B5 | **Long-run drift.** Over 2,000 days, tools reach 2× and weapons 1.9× base price, and hunger creeps to 12 by the end. The baseline isn't stationary beyond about a year. | Calibration, medium | Investigate tool wear against smith capacity; add a 2,000-day stationarity check to `calibrate.py`. |
| B6 | **A closed world posts no quests.** With no outside stock, a mine collapse gives 0 contracts: every candidate is "infeasible" because nothing can be imported or bought. | Design gap, low | Add contracts that can be fulfilled by *producing* (fund a smith, haul from the mine). |
| B7 | `sim.step(-5)` silently does nothing, and unknown ids raise a bare `KeyError`. | Polish | Raise `ValueError` with a clear message. |
| B8 | Producers pause in sync (visible as baseline dips). Already listed in RESULTS.md. | Known | Randomise each NPC's unsold-stock threshold. |

## 3. Making the visuals more intuitive

### Charts (highest value; each is small to fix)

1. **"Production per day" squashes three goods to the floor.** Food runs at about 100 a day,
   while ore, tools and weapons run at 2-25, all on one axis. Use **one small chart per good**,
   or index every good to **% of its normal level** (100% = pre-shock average). A shock then
   reads the same way for every good.
2. **"Prices" hides food.** Food costs about 3 and weapons about 30, so food is a flat line.
   Plot **price as % of base price** with a 100% reference line ("normal price").
3. **"Unmet demand" opens with a fake crisis.** Days 0-8 are a start-up transient (smiths
   filling stocks) that looks like a shortage before any shock. Grey out a "warm-up" band, or
   start the charts at day 10, and show unmet demand as **% of demand** so goods are comparable.
4. **Connect the causal chain to the chart.** Every measured step in the chain already stores
   its metric key. Make each step clickable so the evidence chart shows *that* metric, with its
   baseline and threshold. This turns "trust me" into "see for yourself", and it's the
   feature's main selling point.
5. **Shock shading** uses the UI's gold accent, which also means "selected" and "primary
   action". Use a neutral hatch for shocks, and put the shock label above the plot so it never
   sits on a line.
6. **Colours are reused across charts.** Blue means food in the economy charts and the Miners
   Guild in the treasury chart. Give guilds their own hues, or label lines directly at their
   ends.
7. **The treasury chart's y-axis starts at about 600**, exaggerating small changes. Start it at
   0, and show escrowed coin as a lighter band (this also fixes B2 visually).

### Layout and flow

8. **The header takes a quarter of the screen** at 1280 px, and the control row wraps. Put the
   brand line, day counter, time controls and shock menu in one compact sticky bar, and move
   the intro text into "How it works".
9. **Add a plain-language summary above the chain**, for example: *"The mine collapsed 14 days
   ago. Smiths ran out of ore. The Blacksmiths Guild will pay 363 coin for 31 ore."* The
   detailed chain stays below for people who want proof.
10. **Show quest economics on each card:** estimated profit = reward − cheapest sourcing cost
    (caravan or market), and days left as a small progress bar. Players decide on profit and
    time, not on reward alone.
11. **Highlight the selected quest on the map.** Ring the requester and beneficiaries, and
    pulse the site where the shock hit. The map currently shows 99 identical blue dots and
    carries little information.
12. **Make the map show flows, not just people:** road thickness for units shipped today, a
    fill gauge on each site for its stockpile, and dot size for wealth. Then a shock is
    *visible* (the mine road goes thin) without opening a chart.
13. **First-run guidance:** three dismissible callouts: "1 Read why", "2 Accept and source",
    "3 Advance time and deliver".
14. **Translate jargon on the board:**
    - "Guild supply" → "Guild order";
    - "Haulage" → "Transport job";
    - "covered by pool 344" → "344 needs already covered by a guild order".
15. **Turn the event log into a chronicle.** Add auto-detected economic events (price spikes,
    production drops, guild emergencies) as readable lines with icons, not a mostly empty
    table.
16. **NPC table:**
    - equipment condition as a % bar, not 0.3;
    - filters for profession, guild and state;
    - clicking a row opens a profile (wallet and output over 30 days) and highlights the NPC
      on the map.

## 4. Feature ideas (ranked by value for effort)

| # | Feature | Why it helps | Effort |
|---|---|---|---|
| F1 | **Clickable evidence**: chain step → chart and map highlight (UX items 4 and 11) | Makes provenance self-evidently true; the strongest demo moment | S-M |
| F2 | **Relief and loan contracts for poverty traps**: the town or a guild funds wages or a tool loan, and the player delivers coin or tools on credit | Fixes B3 and answers RESULTS finding 3: quests that restore purchasing power | M |
| F3 | **Counterfactual compare mode**: re-run the same seed without your actions, side by side ("what if I hadn't delivered?") | Shows off determinism; designers love it | M |
| F4 | **Live designer knobs**: sliders for the main parameters (wear, capacity, premiums, thresholds) that re-run instantly | Makes it a tuning tool for studios, not just a demo | M |
| F5 | **Quest economics and plain-language summaries** (UX items 9 and 10) | Faster understanding in the first 30 seconds | S |
| F6 | **Indexed charts and small multiples** (UX items 1-3) | Charts readable at a glance | S |
| F7 | **Chronicle**: auto-written narrative of the run from the evidence records | Great for case studies, videos and players | M |
| F8 | **Run report export**: Markdown or HTML with every quest's chain, outcomes and charts | Portfolio and post-mortem artefact | S |
| F9 | **Per-capita scaling** of treasuries and stocks (B4), with a "population" slider | Lets studios try 1,000+ NPC towns | S |
| F10 | **HTTP/JSON API** (FastAPI over `Simulation`) | Engine integration path for Unity, Godot and Unreal prototypes | M |
| F11 | **Multi-settlement trade and caravan routes** | Regional prices; escort and arbitrage quests | L |
| F12 | **NPC memory and relationships** (who helped me), feeding reputation and rewards | Quests start to feel personal | L |
| F13 | **LLM dialogue that only reads the provenance** (never decides) | Flavour text grounded in verified facts | M |

## 5. Suggested next batch (about 4-6 h)

> Now scheduled as M13-M16 in [ROADMAP.md](ROADMAP.md), alongside relief and loans, futures, smuggling and run reports.

1. **Fix the bugs:** B1, B2 and B7, with tests. About 30 min.
2. **Charts:** indexed charts and small multiples, warm-up band, neutral shock shading, zero
   baselines, distinct guild colours (UX items 1-3 and 5-7). About 1.5 h.
3. **Clickable evidence and map highlight** (F1). About 1.5 h.
4. **Quest card profit and plain-language summary, compact header, jargon pass** (UX items
   8-10 and 14). About 1 h.
5. **"Why no quests?" panel** (B3, display only). About 30 min. Relief contracts (F2) as the
   following step.
