# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Seeded random streams.

Each subsystem draws from its own named stream, so adding a random draw in one place never shifts
the numbers another subsystem sees. String seeds are hashed with SHA-512 by ``random.Random``,
which is stable across processes and Python versions (unlike ``hash()``).
"""

from __future__ import annotations

import random


class RngStreams:
    def __init__(self, seed: int) -> None:
        self.seed = seed
        self._streams: dict[str, random.Random] = {}

    def stream(self, name: str) -> random.Random:
        rng = self._streams.get(name)
        if rng is None:
            rng = self._streams[name] = random.Random(f"questless:{self.seed}:{name}")
        return rng

    def getstate(self) -> dict[str, object]:
        return {name: rng.getstate() for name, rng in sorted(self._streams.items())}

    def setstate(self, state: dict[str, object]) -> None:
        for name, rng_state in state.items():
            self.stream(name).setstate(rng_state)  # type: ignore[arg-type]
