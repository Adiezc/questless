# Crypto, blockchain and fair play: an assessment for a 2030s MMO

Status: design analysis, 2026-10-21. Facts are as of mid-2026; check the status of the projects
named here before quoting them.

**The question:** could crypto and blockchain technology help a 2030s MMO that is
- **not pay-to-win;**
- funded only by the box price and monthly subscriptions;
- **one player per character**, so bots and EVE-style multiboxing (one person running many
  accounts) don't make normal play boring?

**Short answer:** take the *cryptography* and leave the *crypto*. Hash chains, Merkle proofs,
signatures and commit-reveal schemes give players real guarantees (history can't be rewritten,
crises weren't rigged, my balance is what you say it is). Tradable tokens and NFTs work *against*
every one of the goals above: they turn play into income, and income attracts bots, farmers and
multiboxers. Questless builds the useful half as milestone M30, with no chain, no tokens and no
wallets.

## 1. What a blockchain actually provides

A public blockchain bundles three things:
1. **A shared, append-only record** that no single operator can rewrite.
2. **Transferable assets** (tokens, NFTs) that move between people without the operator's
   permission, including outside the game.
3. **Public verifiability:** anyone can check the record.

A subscription MMO has one operator by design: the studio runs the servers, balances the game
and moderates it. So the question is which of the three properties are still worth having when
there's a trusted operator anyway.

## 2. Each goal, and what serves it best

| Goal | Does blockchain help? | Better tool | In Questless |
|---|---|---|---|
| Players can trust the economy isn't rigged | Partly: a public record proves history wasn't changed | Hash-chained logs plus commit-reveal, optionally anchored somewhere public | M30 |
| History can't be quietly rewritten | Yes, but a hash chain with published roots gives the same tamper evidence | Daily roots, like Certificate Transparency logs | M30 |
| I can prove what I own or achieved | Yes, but non-transferable proofs don't need a chain | Signed statements and Merkle proofs | M30.2 |
| Not pay-to-win | **Harmful:** tradable assets let money buy power through secondary markets the studio can't control | No real-money exits; rewards that can't be transferred | M31.5 |
| One player per character, no bots | **Harmful:** earning tokens makes running many accounts and bots profitable | Paid subscriptions per character, payment and device checks, economic detection | M31 |
| Balance changes and fixes | **Harmful:** immutable assets resist rebalancing; "my NFT got nerfed" becomes a financial grievance | Normal patches, checked by economy CI | M23 |
| Players' right to have data deleted | **Conflicts:** data written to a public chain can't be erased (GDPR's right to erasure) | Keep personal data off any public record; publish only hashes | M25 tiers |
| The world survives if the studio closes | Weakly: tokens survive, but the game that gives them meaning doesn't | Publish the engine and save archives (Questless is MIT and replayable) | Persistence |

## 3. Where blockchain-style technology genuinely helps

1. **Provable fairness.** The studio publishes a hash of tomorrow's shocks and seed today and
   reveals them tomorrow. Players can check that the drought wasn't timed to wipe out one guild.
   This needs only SHA-256, not a chain.
2. **An auditable central bank.** If the game prints money (M20), every mint and burn sits in a
   hash-chained log with its reason and evidence. Players can audit monetary policy the way
   people audit real central banks' published accounts.
3. **Public anchoring.** If players don't trust the studio's own website to keep roots unchanged,
   the daily root (32 bytes) can be written to a public transparency log or a public chain. That's
   one tiny write per day, paid by the studio. Players never need a wallet. This is the single
   place a real blockchain might earn its keep.
4. **Portable, non-transferable credentials.** "This player ran the Blacksmiths Guild through
   the Great Collapse" as a signed, verifiable statement another game or a CV can check. It must
   be non-transferable, or it becomes a tradable status good and the problems in §4 return.
5. **Interoperable quests.** The Open Quest Protocol idea (quests as signed, verifiable JSON) lets
   games exchange explainable quests. Signatures are enough; no shared chain is needed.

## 4. Drawbacks, with evidence

- **Financialisation brings bots and multiboxing.** When play earns tradable tokens, running ten
  accounts earns ten times as much. Axie Infinity's 2021-22 boom ran on "scholarships", where
  account owners rented accounts to players who played for income, and its in-game token
  collapsed when new money stopped arriving. That is the opposite of one player per character.
- **Pay-to-win through the back door.** If items can be sold for real money anywhere, richer
  players can buy power even if the studio sells none directly.
- **Security.** Bridges and wallets are high-value targets. The Ronin bridge used by Axie
  Infinity lost over US$600 million in a March 2022 hack.
- **Player and platform rejection.** Valve's Steam rules have barred games built on blockchain
  that issue or trade crypto or NFTs since October 2021. Mojang banned NFTs in Minecraft in
  July 2022. GSC Game World dropped NFT plans for S.T.A.L.K.E.R. 2 in December 2021 after a
  backlash, and Ubisoft's Quartz NFT platform was shut down within months of its 2021 launch.
- **Regulation.** Tradable tokens can fall under financial-services rules (the EU's MiCA
  regulation has applied in full since the end of 2024), securities law, gambling and loot-box
  rules, anti-money-laundering checks and tax reporting. A subscription game avoids all of that.
- **Immutability vs. game design.** Designers need to rebalance, roll back exploits and fix
  duplication bugs. A permanent public record of tradable assets makes every fix a dispute.
- **Support and usability.** Lost keys, scams and fees are support costs a subscription game
  doesn't otherwise have.
- **Energy** is mostly no longer an argument against modern proof-of-stake chains, so this
  assessment doesn't rely on it.

**Still being tested:** CCP Games, the makers of EVE Online, have been experimenting with
blockchain in *EVE Frontier*. It's the most serious attempt by an established MMO studio and worth
watching for evidence either way.

## 5. Recommendation for a subscription, one-character, not-pay-to-win MMO

1. **No tokens, NFTs, on-chain currency or player wallets.** Coin and items stay inside the game,
   with no official real-money exit.
2. **Use the cryptography:** a hash-chained journal, daily state roots, Merkle proofs of a player's
   own holdings, commit-reveal for scheduled events, signed save files and bug reports. (M30)
3. **Optionally anchor daily roots publicly** if players ask for it. One write per day, invisible
   to players.
4. **Make multiboxing pointless rather than just forbidden** (§6).
5. **Keep personal data off any public record.** Publish hashes, never identities.

## 6. One person, one character: a layered approach

No single check works on its own. The layers below reinforce each other.

| Layer | What it does | Who builds it |
|---|---|---|
| **Price** | One subscription per character makes each extra account cost real money every month. | Studio billing |
| **Identity at sign-up** | One active subscription per verified payment method and household rules; passkeys and device attestation make mass account creation expensive. | Account platform |
| **Proof of personhood (optional)** | 2030s "unique human" schemes exist, but they raise privacy concerns (biometrics are special-category data under GDPR) and exclude people. Offer at most as an opt-in, never as a requirement. | Account platform |
| **Economic detection** | The ledger shows value funnelled from alts to a main, circular trades and off-market prices; each flag carries an evidence chain a human reviewer can check. | **Questless M31** |
| **Behaviour detection** | Timing that's too regular, identical action sequences across accounts, concurrent sessions; deterministic replay lets reviewers re-watch exactly what happened. | **Questless M31 and M28** |
| **Design that removes the payoff** | Caps per verified person rather than per character; rewards that can't be transferred; diminishing returns on repeated identical jobs; quests that need decisions, not repetition. | **Questless M31.5** |
| **Due process** | False positives happen. A flagged player sees the evidence and can appeal; the court system (M29) and replays make that cheap. | **Questless M29** |

The design goal: a person running five characters should earn no more than one attentive player,
and should be easy to spot if they try.

## 7. What Questless will build

- **M30, tamper-evident world log (4 h):** hash-chained journal, Merkle proofs, commit-reveal for
  shocks, `questless audit`, and an optional anchor interface with no chain dependency.
- **M31, one-person-one-character safeguards (8 h):** multiple players, a bot league with colluding
  alts, ledger and behaviour signals, and design levers, with false-positive rates reported
  honestly.

Details: [ROADMAP.md](ROADMAP.md) and [BUILD_GUIDE.md](BUILD_GUIDE.md#m30-tamper-evident-world-log).
