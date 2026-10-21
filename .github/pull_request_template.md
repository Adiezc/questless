## What and why

<!-- Which task is this (e.g. M13.1)? Link the issue: "Closes #123". What changed, and why? -->

## How it was tested

<!-- New or changed tests, and what they prove. For UI changes, a screenshot. -->

## Checklist

- [ ] Linked to an issue or a build-guide task
- [ ] Tests added or updated, and they fail without the change
- [ ] `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] `uv run pytest` passes (including the guarantee tests)
- [ ] `uvx bandit -r src app experiments -ll` reports no medium or high findings
- [ ] No secrets, personal data or real player data added
- [ ] Docs updated if behaviour changed (README, SIMULATION_SPEC, ROADMAP status)
- [ ] AI tools used (if any) are named here, and I can explain every line: <!-- e.g. none -->
