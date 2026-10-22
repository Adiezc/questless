# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Questless Gymnasium environment (M24.3).

Standard RL environment compatible with gymnasium.Env, Stable-Baselines3,
and Farama Foundation env checkers.
"""

from __future__ import annotations

from typing import Any

import gymnasium as gym
import numpy as np

from questless.api import Simulation
from questless.contracts.model import Status
from questless.gym.impact import score
from questless.gym.spaces import (
    GOODS_COUNT,
    MAX_TOP_CONTRACTS,
    QTY_BUCKETS,
    VERB_ACCEPT,
    VERB_BUY,
    VERB_CARAVAN,
    VERB_DELIVER,
    get_action_space,
    get_observation_space,
)
from questless.player import ActionError, apply_action
from questless.sim.entities import PLAYER
from questless.sim.ledger import GOODS, Asset


class QuestlessEnv(gym.Env):
    metadata = {"render_modes": ["text"], "render_fps": 10}

    def __init__(
        self,
        scenario_path: str = "scenarios/baseline.toml",
        max_days: int = 60,
        render_mode: str | None = None,
    ) -> None:
        super().__init__()
        self.scenario_path = scenario_path
        self.max_days = max_days
        self.render_mode = render_mode

        self.action_space = get_action_space()
        self.observation_space = get_observation_space()

        self.sim: Simulation | None = None
        self.seed_val: int = 42
        self.current_score: float = 0.0

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
        super().reset(seed=seed)
        self.seed_val = seed if seed is not None else 42
        self.sim = Simulation.from_scenario(self.scenario_path, seed=self.seed_val)
        self.current_score = 0.0

        obs = self._get_obs()
        info = {"tick": 0, "impact_score": 0.0}
        return obs, info

    def step(
        self, action: np.ndarray | list[int]
    ) -> tuple[dict[str, np.ndarray], float, bool, bool, dict[str, Any]]:
        if self.sim is None:
            raise RuntimeError("Call reset() before step()")

        world = self.sim.world
        verb, target_idx, good_idx, qty_idx = action

        good = GOODS[good_idx % GOODS_COUNT]
        qty = QTY_BUCKETS[qty_idx % len(QTY_BUCKETS)]
        contracts = self._get_top_contracts()

        # Execute player action if feasible
        try:
            if verb == VERB_ACCEPT and target_idx < len(contracts):
                c = contracts[target_idx]
                if c.status == Status.OPEN:
                    apply_action(world, "accept", contract_id=c.id)
            elif verb == VERB_DELIVER and target_idx < len(contracts):
                c = contracts[target_idx]
                if c.status == Status.ACCEPTED and c.accepted_by == PLAYER:
                    apply_action(world, "deliver", contract_id=c.id)
            elif verb == VERB_BUY:
                apply_action(world, "buy", good=str(good), qty=qty)
            elif verb == VERB_CARAVAN:
                apply_action(world, "caravan", good=str(good), qty=qty)
        except ActionError:
            # Illegal/infeasible action: no-op without terminating
            pass

        # Advance world by 1 day
        world.step(1)

        # Compute counterfactual reward
        new_score = score(world, self.scenario_path, self.seed_val)
        reward = float(new_score - self.current_score)
        self.current_score = new_score

        terminated = world.tick >= self.max_days
        truncated = False
        obs = self._get_obs()
        info = {"tick": world.tick, "impact_score": self.current_score}

        return obs, reward, terminated, truncated, info

    def _get_top_contracts(self) -> list:
        if self.sim is None:
            return []
        board = self.sim.world.contracts
        return sorted(
            [c for c in board.contracts.values() if c.status in (Status.OPEN, Status.ACCEPTED)],
            key=lambda c: c.reward,
            reverse=True,
        )[:MAX_TOP_CONTRACTS]

    def _get_obs(self) -> dict[str, np.ndarray]:
        if self.sim is None:
            return {
                "coin": np.zeros((1,), dtype=np.float32),
                "holdings": np.zeros((GOODS_COUNT,), dtype=np.float32),
                "prices": np.zeros((GOODS_COUNT,), dtype=np.float32),
                "contracts": np.zeros((MAX_TOP_CONTRACTS, 4), dtype=np.float32),
            }

        world = self.sim.world
        coin = float(world.ledger.balance(PLAYER, Asset.COIN))
        holdings = [float(world.ledger.balance(PLAYER, g)) for g in GOODS]
        prices = [float(world.prices.get(g, 10.0)) for g in GOODS]

        contracts = self._get_top_contracts()
        contracts_mat = np.zeros((MAX_TOP_CONTRACTS, 4), dtype=np.float32)
        for i, c in enumerate(contracts):
            good_idx = GOODS.index(c.good) if c.good in GOODS else 0
            deadline_delta = max(0, c.deadline_tick - world.tick)
            contracts_mat[i] = [
                float(c.reward),
                float(c.qty),
                float(deadline_delta),
                float(good_idx),
            ]

        return {
            "coin": np.array([coin], dtype=np.float32),
            "holdings": np.array(holdings, dtype=np.float32),
            "prices": np.array(prices, dtype=np.float32),
            "contracts": contracts_mat,
        }

    def render(self) -> str | None:
        """Text mode rendering for LLM agents (M24.4)."""
        if self.render_mode != "text" or self.sim is None:
            return None

        world = self.sim.world
        contracts = self._get_top_contracts()
        lines = [
            f"=== Day {world.tick} ===",
            f"Player Coin: {world.ledger.balance(PLAYER, Asset.COIN)}",
            f"Open Contracts: {len(contracts)}",
        ]
        for c in contracts:
            lines.append(
                f"  - [{c.id}] {c.kind}: Deliver {c.qty} {c.good.value} (Reward: {c.reward})"
            )
        output = "\n".join(lines)
        return output
