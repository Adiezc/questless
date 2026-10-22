# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Gymnasium observation and action spaces for Questless (M24.2)."""

from __future__ import annotations

import numpy as np
from gymnasium import spaces

from questless.sim.ledger import GOODS

# Fixed dimensions
MAX_TOP_CONTRACTS = 5
GOODS_COUNT = len(GOODS)  # food, iron_ore, tools, weapons

# Actions: [verb, target_index, good_index, qty_bucket]
# verb: 0=noop, 1=accept, 2=deliver, 3=buy, 4=caravan
VERB_NOOP = 0
VERB_ACCEPT = 1
VERB_DELIVER = 2
VERB_BUY = 3
VERB_CARAVAN = 4

QTY_BUCKETS = [1, 2, 5, 10, 20]


def get_action_space() -> spaces.MultiDiscrete:
    """MultiDiscrete([5 verbs, 5 target contracts, 4 goods, 5 qty buckets])."""
    return spaces.MultiDiscrete([5, MAX_TOP_CONTRACTS, GOODS_COUNT, len(QTY_BUCKETS)])


def get_observation_space() -> spaces.Dict:
    """Fixed-size Dict space: wallet, stocks, prices, top K contracts."""
    return spaces.Dict(
        {
            "coin": spaces.Box(low=0, high=1e6, shape=(1,), dtype=np.float32),
            "holdings": spaces.Box(low=0, high=1e5, shape=(GOODS_COUNT,), dtype=np.float32),
            "prices": spaces.Box(low=0, high=1e4, shape=(GOODS_COUNT,), dtype=np.float32),
            "contracts": spaces.Box(
                low=0,
                high=1e5,
                shape=(MAX_TOP_CONTRACTS, 4),  # [reward, qty, deadline_delta, good_idx]
                dtype=np.float32,
            ),
        }
    )
