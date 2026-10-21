# Security policy

## Reporting a vulnerability

Please **don't open a public issue** for security problems. Instead, use GitHub's private
reporting: go to the repository's **Security** tab and choose **Report a vulnerability**. Only the
maintainer can see the report.

Include what you found, how to reproduce it (a save file or a scenario is ideal, since runs replay
exactly), and its impact. You'll get an acknowledgement as soon as possible; this is a volunteer
project, so please allow reasonable time for a fix before disclosing publicly.

## Scope

Questless is a research prototype that runs locally. Relevant reports include:
- code execution or file access from a crafted scenario (TOML) or save file (JSON);
- ways to break the engine's guarantees (creating coin or goods, bypassing escrow, forging
  evidence that `verify()` accepts, replays that diverge);
- vulnerable dependencies;
- once built: escapes from the standing-orders sandbox (M37) or leaks across the wiki's
  visibility tiers (M25).

## What CI checks on every change

| Check | Tool |
|---|---|
| Lint and formatting | ruff |
| Tests, including conservation, determinism and provenance guarantees | pytest |
| Security lint of the code | bandit (medium and high findings fail the build) |
| Known vulnerabilities in dependencies | pip-audit |
| Committed secrets | gitleaks |
| Dependency updates | Dependabot |

How to run the same checks locally is in [CONTRIBUTING.md](CONTRIBUTING.md#the-checks-every-pull-request-must-pass).
