# Blueprint: a 2030s megaserver world

Status: vision document, 2026-10-21. Technology forecasts are informed guesses, labelled by how
far along each technology is today (mid-2026).

QUESTLESS has two halves:
- **The engine (real).** A small, tested, deterministic economy you can run today. Each milestone
  adds a working piece that proves an idea at small scale.
- **The blueprint (vision).** How those pieces would fit together in a commercial MMO of the
  2030s: one world for every player, at EVE Online's scale, with No Man's Sky's sense of a vast
  explorable universe, in either a fantasy or a science-fiction setting.

Every section below says which parts the engine demonstrates and which stay on paper.

## 1. The target

| Property | Choice | Why |
|---|---|---|
| **One megaserver** | Every player is in the same world. No shards, no language servers. | A single economy and history; every crisis matters to everyone. EVE Online has run one shared world since 2003. |
| **One person, one character** | One living character per subscription and per verified person (dynasties pass it on). | No multiboxing; see [BLOCKCHAIN.md §6](BLOCKCHAIN.md#6-one-person-one-character-a-layered-approach). |
| **Business model** | Box price and subscription only; nothing for sale that affects play; no real-money exits. | Not pay-to-win; no reason to farm. |
| **Setting** | Fantasy or science fiction, as data. | The same engine runs a medieval continent or a galaxy. |
| **Scale of place** | One planet, or many star systems. | The world is a graph of places either way (§3). |

## 2. One megaserver: the architecture

The engine's existing rules (one ledger, escrow first, determinism, replay) are the same rules a
megaserver needs. The difference is distribution.

```
            ┌──────────── one logical world ────────────┐
 players ─► │  region A   region B   region C  ...      │ ◄─ millions of regions,
            │  (full sim) (aggregate) (dormant)          │    thousands active
            │      │  ▲         │  ▲                    │
            │      ▼  │ messages▼  │  (goods, coin, people in transit)
            │   transit ledger: everything between regions │
            └────────────────────────────────────────────┘
               │ action logs + daily roots ─► replay, audit, wiki, reports
```

1. **Regions as the unit of simulation.** The world is partitioned into regions (a valley, a
   city, a star system). Each region has its own ledger and ticks deterministically on its own
   worker.
2. **Messages between regions.** Anything leaving a region (a caravan, a freighter, a migrant,
   a payment) becomes a message delivered at a later tick, held meanwhile on a transit ledger.
   Global conservation = the sum of region ledgers + the transit ledger. QUESTLESS's
   `in_transit` account for caravans is the small-scale version of this.
3. **Simulation level of detail.** Regions with players run every NPC as an agent. Busy regions
   without players run on aggregates (production and consumption per profession, not per NPC).
   Distant regions sleep and are fast-forwarded when someone arrives. Whatever the level of
   detail, coin and goods still move only through the ledger, so switching levels can't create
   value. (Real in v0.4: M34.)
4. **Lazy universe.** As in No Man's Sky, places are generated from a seed when first visited:
   terrain, resources and starting NPCs. A galaxy can have billions of places while only the
   settled thousands are simulated.
5. **Hot spots.** When a region is overloaded (a siege, a market crash), it slows its own clock
   rather than dropping events. EVE introduced this "time dilation" in 2011. Deterministic ticks
   make it safe: a slower tick is still the same tick.
6. **Event sourcing.** The action log plus periodic checkpoints is the record of truth. Replays
   (M28), audits (M30), wikis (M25) and reports (M26) are all derived from it.
7. **Region-level markets.** Each region clears its own market; prices differ by region, which is
   what makes trade, roads and smuggling worth doing. A global "exchange" is just a region whose
   goods arrive late.

## 3. Fantasy or science fiction: one engine, two skins

Everything setting-specific is data:

| Engine concept | Fantasy | Science fiction |
|---|---|---|
| Place | Village, valley, kingdom | Station, planet, star system |
| Route | Road, river, mountain pass | Hyperspace lane, jump gate |
| Raw resource | Iron ore, timber, fish | Ice, rare metals, gas giant fuel |
| Producer | Miner, farmer, smith | Driller, hydroponics tech, fabricator |
| Transport | Caravan | Freighter |
| Shock | Mine collapse, drought, bandits | Reactor failure, solar flare, pirates |
| Renewable commons | Forests, fish | Algae fields, atmospheric harvest |
| Governance | Mayor, guilds, kingdoms | Station council, corporations, federations |

**One planet or a galaxy** is a choice of topology: places are nodes, routes are edges with a
travel time. A single continent is a dense graph with slow edges; a galaxy is a sparse graph of
dense clusters. (Real in v0.4: M33 adds theme packs and topology as config, and runs the same
scenario in both skins.)

## 4. 2030s technologies that make it better

Readiness: **now** = in production today; **maturing** = works today, needs to get cheaper or
better; **emerging** = early, plausible by the 2030s; **speculative** = not planned.

### Simulation and scale

| Technology | Readiness | What it enables | Stepping stone in QUESTLESS |
|---|---|---|---|
| **Learned surrogate simulators** (neural networks trained to imitate a slow simulation, already used in weather forecasting) | maturing | Fast-forward millions of dormant regions in milliseconds, checked against the full simulation on samples and replaced by it when it drifts | **M40:** train a surrogate on QUESTLESS runs and measure its error honestly |
| **WebAssembly sandboxes** | now | Run player-written rules and community mods safely and deterministically, with fixed fuel budgets | **M37** starts with a tiny interpreted rule language; Wasm is the scale-up path |
| **Data-oriented engines** (entity-component systems) | now | Millions of agents per server | The engine's per-NPC rules port directly to component systems |
| **Edge data centres and low-orbit satellite internet** | maturing | Lower latency worldwide, so one megaserver is fair to players everywhere | Regions hosted near their players (blueprint) |
| **Columnar analytics and event streaming** | now | Economic reports and wikis for millions of players without slowing the game | **M25, M26** produce the same reports at small scale |

### Trust, identity and privacy

| Technology | Readiness | What it enables | Stepping stone |
|---|---|---|---|
| **Zero-knowledge proofs** (zkVMs) | emerging | The studio proves the economy followed its published rules *without* revealing private state, such as NPC wallets or hidden causes | **M30** hash chains and Merkle proofs; ZK is the next step |
| **Privacy-preserving digital identity** (verifiable credentials; the EU's Digital Identity Wallet under eIDAS 2.0) | maturing | "One person, one character" proven without the studio storing anyone's ID: the wallet says "unique adult" and nothing else. Optional, with an equal route for players without a wallet; designed around the GDPR in [PRIVACY_AND_IDENTITY.md](PRIVACY_AND_IDENTITY.md) | **M31** signals, **M42** privacy as code |
| **Confidential computing** (secure enclaves) | now | Developer-tier data processed so even operations staff see only what their role allows, with every access logged | **M25** tiers, **M42** roles and access log |

### Players and presentation

| Technology | Readiness | What it enables | Stepping stone |
|---|---|---|---|
| **Real-time speech-to-speech translation** | maturing | One world with no language servers, with English encouraged as the common language and learning built in | **M43** language bridge |
| **Small on-device language and voice models** | maturing | NPCs that talk naturally about *why* things happened, reading only verified provenance; they never decide anything | Provenance as structured data (v0.1) |
| **Generative 3D and procedural content** | maturing | Towns, roads and ruins built automatically from the economy's state and history | **M35** produces the data (where roads and buildings should be) |
| **Neural rendering** (e.g. Gaussian splatting) | maturing | Huge, detailed scenes on modest hardware and phones | Blueprint only |
| **AR glasses and phones as companion clients** | maturing | Check your standing orders and contracts during the day; play the economy without the full client | Contract feed and companion play (backlog) |

### AI in the world

| Technology | Readiness | What it enables | Stepping stone |
|---|---|---|---|
| **AI agents as declared citizens** | emerging | AI players labelled as such, playing under exactly the same rules, limits and action budgets as people | **M24** environment, **M37** shared action budget |
| **Steward AI** | emerging | Capable NPCs that keep the world fun and fair, help or hurt players, and steer them towards playing together; optimised for community health, never for time spent | **M44** steward NPCs |
| **Policy simulation (digital twins)** | now in cities and industry | Preview a law, tax or treaty before players vote on it | **M23** economy diff, referendum preview (backlog) |

### Hype check: not planned

- **Tradable tokens and NFTs:** they work against fair play; see [BLOCKCHAIN.md](BLOCKCHAIN.md).
- **Quantum computing:** no clear use in a game economy in this period.
- **Brain-computer interfaces:** too early, and the privacy risks are serious.

## 5. What the engine will prove, and what stays on paper

| Idea | Real in QUESTLESS | Blueprint only |
|---|---|---|
| Conservation across a distributed world | Region ledgers + transit (M34) | Thousands of workers, failover |
| Simulation level of detail | Full ↔ aggregate ↔ dormant regions with conservation (M34) | Automatic placement on servers |
| Fast-forwarding dormant regions | Surrogate experiment with measured error (M40) | Production-grade surrogates |
| A map that grows from the economy | Roads and towns as data (M35) | Generated 3D art |
| Commons and ecology | Population models and community rules (M36) | Full ecosystems |
| Fair automation instead of bots | Rule language with shared action budgets (M37) | Wasm sandbox, mobile rule editor |
| Player-posted quests | Same validation as NPC quests (M38) | Quest discovery at scale |
| Treaties, sanctions, embargoes | Bonded treaties between regions (M39) | Diplomacy UI |
| Fantasy and sci-fi | Two theme packs on one scenario (M33) | Art and audio |
| Verifiable fairness | Hash chains, commit-reveal (M30) | Zero-knowledge proofs |
| One person, one character | Detection and design levers (M31), privacy as code (M42) | Identity wallets |
| A common language | Exact translation of structured text, learning mode (M43) | Live voice translation |
| AI that keeps the world fun | Steward NPCs in the bot league (M44) | Trained stewards at scale |
| Real-world skills | Skills passport (M45) | School and university programmes |

The roadmap's v0.4 scope ([ROADMAP.md](ROADMAP.md#v04-scope-the-megaserver-foundations)) builds
the "real" column.
