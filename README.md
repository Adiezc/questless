# QUESTLESS

**Emergent quests from living worlds.**

QUESTLESS is an open-source, deterministic quest-economy engine for MMO-style worlds. A settlement of
rule-based NPCs produces, trades and consumes goods. When they hit needs they cannot meet, the engine
turns those needs into funded, validated player contracts, each with a recorded answer to
*"Why does this quest exist?"*

> Status: early development (milestone M0 of [the plan](docs/PLAN.md)). Nothing playable yet.

## Quickstart (development)

```bash
uv sync
uv run pytest
uv run questless --version
```

Requires [uv](https://docs.astral.sh/uv/); it installs the pinned Python (3.12) automatically.

## Documents

- [Plan (A–I)](docs/PLAN.md)
- [Critical evaluation and prior art](docs/EVALUATION.md)

## Creator

Created by **Adrian Diez Cuadrado**. Studios interested in collaboration, integration, consulting or
employment: see [CONTACT.md](CONTACT.md).

## Licence

[MIT](LICENSE) © 2026 Adrian Diez Cuadrado. You may use, modify and distribute QUESTLESS, including
commercially, provided the copyright and permission notice is kept in copies or substantial portions
of the software. A credit or a short note if you use it is appreciated, but not required.
