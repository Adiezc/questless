# Contributing to Questless

Questless is a small, working engine plus a large public roadmap for the systems a 2030s
massively multiplayer world would need: explainable economies, courts, diplomacy, ecology, fair
automation, privacy by design, and real-world skills taught through play. Most of the roadmap is
unbuilt, and it's meant to be built in the open.

## Why contribute

- **Build something real and visible.** Every milestone in the [roadmap](docs/ROADMAP.md) is
  broken into issue-sized tasks in the [build guide](docs/BUILD_GUIDE.md), with the files to touch,
  the tests to write and the traps to avoid.
- **Learn transferable skills.** Simulation, invariant testing, event sourcing, privacy and
  security engineering, reinforcement learning, data visualisation and economic design. See
  [SKILLS.md](docs/SKILLS.md#2-skills-for-developers-and-contributors) for learning paths.
- **Get credit.** Merged contributors are credited in the changelog for the release they land
  in, and significant contributors are listed in [AUTHORS.md](AUTHORS.md) (with their consent).
  Your commits stay in the history under your name.
- **No coding needed for some tracks.** Economists, lawyers, teachers and political scientists
  can write lessons and skill tracks (milestones M26 and M47) without touching the engine.

## Suggest ideas

You don't have to write code to shape the project. Ideas that would benefit Questless are welcome:
new mechanics, skill tracks, research it should draw on, or things that confused you. Post them in
[Discussions → Ideas](https://github.com/Adiezc/questless/discussions/categories/ideas) or open an
issue with the **Suggest an idea** template. Good ideas get added to the [roadmap](docs/ROADMAP.md)
with credit to whoever suggested them.

## What gets merged, and what doesn't

To keep everyone's time well spent, pull requests are judged against the roadmap and the
guarantees below.

**Likely to be merged:**
- A task from the build guide (M13.1, M17.3 and so on) that meets its acceptance tests.
- A bug fix with a test that fails before the fix and passes after.
- A lesson, scenario or skill track that follows the formats in the build guide.
- Clearer docs, especially where something confused you.

**Discuss first in an issue** (so you don't build something that can't be merged):
- Anything sized M or L in the build guide.
- New mechanics, backlog ideas, or changes to the roadmap.
- New dependencies.

**Won't be merged:**
- Changes that break a core guarantee (conservation, escrow, provenance, determinism, replay).
- Cosmetic churn: mass reformatting, renaming, or rewording without a reason.
- Code without tests, or tests that don't test the change (for a bug fix, a test that also
  passes without the fix).
- Tradable tokens, NFTs or real-money features (see [BLOCKCHAIN.md](docs/BLOCKCHAIN.md)).
- LLMs making decisions inside the simulation. They may write flavour text from verified
  evidence, never decide outcomes.
- Generated code you can't explain. AI-assisted contributions are welcome; you're responsible for
  understanding, testing and defending every line, and please say in the pull request which tools
  you used.

## Giving everyone a turn

Questless has one maintainer, so review time is the scarce resource. These limits apply to
everyone and keep the queue short enough for every pull request to get a proper review.

- **One claimed issue and one open pull request per person at a time.** Finish or release your
  current claim (say so in the issue) before claiming another. Pull requests over the limit may
  be closed, and you're welcome to reopen them once your earlier one is merged or closed.
- **`good first issue` tasks are for first-time contributors.** Once you've had a pull request
  merged, please leave them for newcomers and pick a `help wanted` issue or a larger build-guide
  task instead.
- **Every bug fix needs a test that fails without the fix.** Before opening the pull request, run
  your new test against `main` (for example `git stash` your source changes, or check out `main`'s
  `src/`) and confirm it fails, then confirm it passes on your branch. Say in the pull request that
  you did this. A test that passes either way doesn't prove the fix.

## How to contribute, step by step

1. **Pick a task.** Browse issues labelled `good first issue` or `help wanted`, or choose a task
   from the [build guide](docs/BUILD_GUIDE.md).
2. **Claim it.** Comment on the issue (or open one titled with the task id, such as
   "M13.1 Reject NaN and infinity in config") so two people don't build the same thing. You can
   hold one claim at a time (see [Giving everyone a turn](#giving-everyone-a-turn)). For M or L
   tasks, add a short design: what you'll change and how you'll test it.
3. **Fork and branch.** Fork the repository and create a branch named after the task, such as
   `m13-1-reject-nan`.
4. **Set up:**
   ```bash
   uv sync --all-extras
   ```
   [uv](https://docs.astral.sh/uv/) installs the pinned Python (3.12) for you.
5. **Build it with tests.** Follow the recipes in
   [BUILD_GUIDE.md Part 3](docs/BUILD_GUIDE.md#part-3-recipes-for-common-changes); they list every
   place a typical change must touch.
6. **Run every check locally** (the same ones CI runs, see below).
7. **Open a pull request** using the template. Link the issue, say what changed and why, and paste
   the check results.
8. **Review.** A maintainer reviews it. Expect questions; most pull requests need one round of
   changes. Once approved, it's squash-merged and you're credited in the changelog.

## The checks every pull request must pass

Run these before opening a pull request. CI runs the same checks and won't merge a red build.

```bash
uv run ruff check .                # lint
uv run ruff format --check .       # formatting (run `uv run ruff format .` to fix)
uv run pytest                      # 150+ tests, including the guarantee tests (~15 s)
uvx bandit -r src app experiments -ll   # security lint: no medium or high findings
uv export --format requirements-txt --all-extras --no-hashes --no-emit-project > /tmp/req.txt
uvx pip-audit -r /tmp/req.txt      # known vulnerabilities in dependencies
```

CI also runs **gitleaks** to make sure no secrets (tokens, keys, passwords) are committed.

**Economy check.** Pull requests that touch `src/`, `scenarios/` or `.questless/` get an automatic
"Economy impact" comment: every scenario runs on 10 seeds against the base branch, and changes
beyond seed-to-seed noise are listed in plain words. The check fails on a broken invariant, on
non-determinism, or when a change breaks a limit in [`.questless/ci.toml`](.questless/ci.toml).
Run it yourself before pushing:

```bash
uv run questless diff --base origin/main
```

**What the guarantee tests check**, and why they matter:

| Test file | Guarantee |
|---|---|
| `tests/test_invariants.py` | Coin and goods are conserved every day; no negative balances; escrow equals live contracts |
| `tests/test_determinism.py` | The same scenario, seed and actions give the same state hash, across processes and hash seeds |
| `tests/test_provenance.py` | Every contract's evidence re-measures, and forged evidence is caught |
| `tests/test_economic_justification.py` | Contracts exist only when their cause exists (the no-shock run produces none) |

If a guarantee test fails, the change is wrong, not the test. Ask in the issue if you're unsure
why.

## Ground rules for code

1. **One ledger.** Change balances only through ledger operations.
2. **Escrow first.** An obligation exists only after its coin is escrowed.
3. **Evidence, not prose.** Decisions carry `Evidence` records that `verify()` can re-check.
4. **Deterministic.** Use the world's named RNG streams; never the `random` module directly, the
   clock, or unordered iteration that affects state.
5. **Replayable.** Player-side changes go through `player.apply_action` with JSON-serialisable
   arguments.
6. **Tuning values in TOML**, not in code.
7. **The engine stays standard-library only.** Optional extras live in `app/`, `experiments/` or
   guarded modules.

## Security and privacy

- Never commit secrets, personal data, or real player data. Use synthetic data in tests.
- Found a vulnerability? Don't open a public issue; follow [SECURITY.md](SECURITY.md).
- Features that touch player data follow [PRIVACY_AND_IDENTITY.md](docs/PRIVACY_AND_IDENTITY.md).

## Conduct

Be kind, be specific, assume good faith. This project follows the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Licence

By contributing, you agree that your contribution is licensed under the [MIT licence](LICENSE),
like the rest of the project.
