# Privacy and identity: stopping bots without collecting identities

Status: design, 2026-10-21. **This is an engineering design, not legal advice.** Laws differ by
country and will change before the 2030s; a real launch needs a data protection officer and legal
review. Legal references are to EU law as of mid-2026, because it's the strictest widely used
baseline: the GDPR (Regulation (EU) 2016/679), eIDAS 2.0 (Regulation (EU) 2024/1183, which
creates the EU Digital Identity Wallet) and the AI Act (Regulation (EU) 2024/1689).

**The problem:** a megaserver with one person per character must stop bots and multiboxing. The
obvious fix, collecting ID documents or face scans, is exactly what privacy law discourages and
players distrust.

**The principle: prove, don't collect.** The game learns only what it needs ("this is a real,
unique adult who hasn't got another active character here"), never who the person is.

## 1. The legal constraints that shape the design

| Rule | What it requires | Design consequence |
|---|---|---|
| **Data minimisation** (GDPR Art. 5(1)(c)) | Collect only what's needed for the purpose | No names, ID scans or birth dates; only yes/no claims and a pseudonymous id |
| **Purpose limitation** (Art. 5(1)(b)) | Data collected for anti-cheat can't be reused for marketing | Anti-cheat data lives in its own store with its own access rules |
| **Lawful basis** (Art. 6) | Every processing needs a basis | Subscription data: contract. Anti-cheat signals: legitimate interests, which the GDPR's recital 47 says can include preventing fraud; documented in a legitimate-interests assessment |
| **Special-category data** (Art. 9) | Biometric data used to identify someone is specially protected | No face scans, voiceprints or keystroke-based identification |
| **Automated decisions** (Art. 22) | People have rights when decisions with significant effects are made solely by machine | A ban is never fully automatic: flags go to a trained human with the evidence, and players can appeal |
| **Privacy by design and default** (Art. 25) | Build privacy in, with the most private setting as default | Visibility tiers (M25), pseudonymous ids everywhere, privacy tests in CI |
| **Impact assessment** (Art. 35) | High-risk processing needs a data protection impact assessment | A DPIA template in the repo, updated whenever a milestone touches personal data |
| **Right to erasure** (Art. 17) | People can ask for their data to be deleted | Personal data is never written into the world history; it can be destroyed by deleting keys (§4) |
| **Children** (Art. 8) | Consent for children's data needs a parent below 13-16, depending on the country | Age assurance with a yes/no claim; safer defaults for minors |
| **EU Digital Identity Wallet** (eIDAS 2.0) | Wallets disclose only selected attributes; using one is voluntary, and people who don't must not be disadvantaged | The wallet is one optional route; an equally good path exists without it (§2) |
| **AI transparency and manipulation** (AI Act Art. 50 and Art. 5) | People must know when they're interacting with an AI system unless it's obvious; manipulative techniques that cause significant harm are banned | AI-controlled players are labelled; steward NPCs (M44) optimise for fun and community, never for compulsive play |

Other regimes (the UK GDPR and Online Safety Act, US children's privacy law (COPPA), state
privacy laws) differ in detail but point the same way. The design keeps legal choices in
**jurisdiction profiles** (config), so a 2030s law change is a settings change plus review, not a
rewrite.

## 2. The trust ladder: equal access with or without a wallet

| Level | How a player reaches it | What it unlocks |
|---|---|---|
| **Newcomer** | Free trial, email or passkey only | A starter region; small action budget; nothing of value can leave the region |
| **Citizen** | Paid subscription plus a device passkey | The full world; the standard action budget |
| **Trusted citizen**, route A | An optional identity wallet presents three claims: "over 16" (or the local age), "unique person for this service" and a **service-specific pseudonym** | Higher limits: run a guild treasury, sit on a jury, post large contracts |
| **Trusted citizen**, route B | 60 days as a citizen with no integrity flags, plus a second payment check | The same as route A |

Route B exists so nobody has to use a wallet (eIDAS requires that), and so players in countries
without wallets aren't locked out. Route A is just faster.

**How "unique for this service" works without tracking:**
- The wallet derives an identifier that is stable for this game but different for every other
  service, so services can't link a person across sites.
- The game stores only that identifier and checks it has no other active character.
- Zero-knowledge versions of this exist in research today and are expected to mature by the 2030s;
  the design doesn't depend on any one scheme.

## 3. Catching bots lawfully

- **Signals:** economic patterns from the ledger (M31: value funnelled to one account, circular
  trades), action timing regularity, identical action sequences, concurrent sessions.
- **Minimised:** features are computed in the moment and stored as aggregates, never as raw
  keystrokes or mouse traces. Retention: 90 days unless a case is open.
- **Fairly decided:** a flag carries its evidence chain. A human reviewer decides; the player is
  told what was found and can appeal to a second reviewer. In-game disputes can go to the in-game
  court (M29); account bans always get human review.
- **Bots aren't worth it in the first place:** standing orders (M37) give everyone legal
  automation with the same action budget, so a bot gains nothing (see
  [BLOCKCHAIN.md §6](BLOCKCHAIN.md#6-one-person-one-character-a-layered-approach)).

## 4. Keeping personal data out of the world

- **Two separate stores.** The world (ledger, action log, wiki, hash chain) contains only random
  player ids. A separate identity store maps random ids to accounts, and it's the only place
  personal data lives.
- **Crypto-shredding.** Each player's personal data is encrypted with their own key. Erasing a
  player means deleting their key and their mapping; the world history stays intact but can no
  longer be connected to the person.
- **The tamper-evident log (M30) never contains personal data,** not even hashed (a hash of an
  email address is still personal data), so erasure never conflicts with immutability.

## 5. Keeping developer data from the wrong developers

The wiki's `dev` tier (M25) is split by role, following least privilege:

| Role | Sees |
|---|---|
| Economy designer | Aggregates and NPC internals; no player data |
| Live-ops | World state and replays with pseudonymous ids |
| Trust and safety | Integrity flags and the id-to-account mapping, case by case |
| Security | Access logs |

- **Every access is logged** into the tamper-evident log (M30), so access can be audited later.
- **Break-glass access** (emergencies) needs a reason, is time-limited and is reviewed afterwards.
- **Confidential computing:** in production, the identity store and anti-cheat analysis run in
  secure enclaves, so even infrastructure operators can't read them. This is blueprint only; the
  engine demonstrates the tiers and the logging.

## 6. Privacy as code (milestone M42)

Making these rules testable, so they don't decay:
- `privacy/data_inventory.toml` lists every personal field: purpose, lawful basis, retention,
  visibility tier.
- A CI test fails if code adds a player-related field that isn't in the inventory.
- The M25 leak test runs for every tier and role.
- A retention job deletes expired signals, with a test.
- A crypto-shredding demo shows erasure working on a save.
- `docs/DPIA_TEMPLATE.md` is filled in for each milestone that touches personal data.

Details: [ROADMAP.md](ROADMAP.md#m42-privacy-as-code-6-h) and
[BUILD_GUIDE.md](BUILD_GUIDE.md#m42-privacy-as-code).
