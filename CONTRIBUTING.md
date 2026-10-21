# Contributing to QUESTLESS

Thanks for your interest. QUESTLESS is a small research prototype, so focused contributions are the
most useful.

## Setup

```bash
uv sync              # creates .venv with Python 3.12 and dev tools
uv run pytest        # run the test suite
uv run ruff check .  # lint
uv run ruff format . # format
```

## Ground rules

1. **Invariant tests must pass.** Coin and goods conservation, no negative balances, contract caps and
   determinism are the core guarantees. A change that breaks one is not mergeable.
2. **Every contract needs a cause.** New contract types must build provenance from recorded evidence,
   with a test showing the contract does not appear without that cause.
3. **Keep the engine dependency-free.** `src/questless/` uses the standard library only. UI code lives
   in `app/`.
4. **Determinism:** use the world's seeded RNG; never call `random` module functions directly, read the
   clock, or iterate over unordered sets when the order affects state.
5. **Tuning values belong in `scenarios/*.toml`**, not in code.

## Pull requests

- Keep each PR to one change, with a short description of *why*.
- Add or update tests.
- Run `uv run pytest` and `uv run ruff check .` before opening it.
- By contributing, you agree that your contribution is licensed under the MIT licence.

## Scope

Out of scope for now: networking/multiplayer, 3D or game-engine clients, combat, and LLMs in the
simulation's decision loop. See the roadmap in [docs/PLAN.md](docs/PLAN.md#i-roadmap).
