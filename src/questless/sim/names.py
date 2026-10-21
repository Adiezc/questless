# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Seeded fantasy-style name generator. Cosmetic only; never affects simulation state."""

from __future__ import annotations

import random

_FIRST_A = ("Al", "Bran", "Cor", "Da", "El", "Fen", "Gar", "Hal", "Is", "Jor", "Ka", "Lor", "Mar")
_FIRST_B = ("a", "ric", "wen", "dor", "is", "ra", "mund", "eth", "an", "ella", "ric", "on", "wyn")
_SURNAME = {
    "farmer": ("Thatch", "Barley", "Furrow", "Meadows", "Sheaf"),
    "miner": ("Delve", "Flint", "Shaft", "Pickett", "Stone"),
    "blacksmith": ("Anvil", "Hammer", "Forge", "Bellows", "Temper"),
    "merchant": ("Coin", "Ledger", "Wagon", "Barter", "Scales"),
    "guard": ("Shield", "Watch", "Halberd", "Gate", "Steel"),
}


def make_name(rng: random.Random, profession: str, taken: set[str]) -> str:
    """Return a unique name; falls back to a numeric suffix once combinations run out."""
    surnames = _SURNAME.get(profession, ("Common",))
    for _ in range(20):
        name = f"{rng.choice(_FIRST_A)}{rng.choice(_FIRST_B)} {rng.choice(surnames)}"
        if name not in taken:
            taken.add(name)
            return name
    base = f"{rng.choice(_FIRST_A)}{rng.choice(_FIRST_B)} {rng.choice(surnames)}"
    n = 2
    while f"{base} {n}" in taken:
        n += 1
    taken.add(f"{base} {n}")
    return f"{base} {n}"
