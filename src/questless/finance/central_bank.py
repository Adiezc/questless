# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Adrian Diez Cuadrado
"""Central bank monetary policy engine and interest rate mechanics (M20).

Defines:
- CPI & Inflation calculation against base consumption basket.
- CentralBank policy state with policy rate, inflation target, mint/burn decisions.
- Discount window lending for guilds in liquidity distress.
- Policy rate transmission to loans, futures carry, and emergency borrowing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import fmean
from typing import TYPE_CHECKING

from questless.contracts.provenance import Evidence
from questless.sim.entities import CENTRAL_BANK, Asset

if TYPE_CHECKING:
    from questless.sim.world import World


@dataclass(slots=True)
class CentralBank:
    policy_rate: float = 0.05  # 5% annual/cycle baseline policy rate
    target_inflation: float = 0.02  # 2% target
    target_band: tuple[float, float] = (0.01, 0.03)  # [1%, 3%] band
    max_rate_change_daily: float = 0.005  # 50 bps daily rate limit to prevent oscillations
    max_daily_mint: int = 500  # Cap on quantitative easing per day
    max_daily_burn: int = 500  # Cap on monetary contraction per day
    penalty_spread: float = 0.03  # 300 bps discount window penalty
    base_basket: dict[Asset, float] = field(default_factory=dict)
    base_basket_cost: float = 0.0
    smoothed_cpi: float = 100.0

    def compute_cpi(self, world: World) -> tuple[float, float]:
        """Compute Consumer Price Index (CPI) and 30-day smoothed inflation (M20.2)."""
        # Form base basket from consumption if not initialized
        if not self.base_basket:
            # Baseline basket based on average daily requirements
            self.base_basket = {Asset.FOOD: 1.0, Asset.TOOLS: 0.1, Asset.IRON_ORE: 0.2}
            self.base_basket_cost = sum(
                qty * world.prices.get(asset, 10.0) for asset, qty in self.base_basket.items()
            )

        current_cost = sum(
            qty * world.prices.get(asset, 10.0) for asset, qty in self.base_basket.items()
        )
        cpi = (current_cost / self.base_basket_cost) * 100.0 if self.base_basket_cost > 0 else 100.0

        # Calculate smoothed inflation over past 30 days
        window = world.stats[max(0, len(world.stats) - 30) :]
        past_cpis = [getattr(s, "cpi", 100.0) for s in window]
        if past_cpis:
            self.smoothed_cpi = float(fmean(past_cpis + [cpi]))
        else:
            self.smoothed_cpi = cpi

        base_ref = past_cpis[0] if past_cpis else 100.0
        inflation = (cpi - base_ref) / base_ref if base_ref > 0 else 0.0
        return round(cpi, 2), round(inflation, 4)

    def execute_policy_step(self, world: World) -> Evidence:
        """Run daily monetary policy decision rule after market clearing (M20.3)."""
        cpi, inflation = self.compute_cpi(world)

        # Check broke-NPC share (NPCs with 0 or near 0 coin)
        npcs = list(world.npcs.values())
        broke_count = sum(1 for n in npcs if world.ledger.balance(n.account, Asset.COIN) < 5)
        broke_share = broke_count / len(npcs) if npcs else 0.0

        # Policy rule:
        # If inflation > target_band upper: hike rate and burn excess coin
        # If inflation < target_band lower and broke share high: cut rate and mint liquidity
        rate_delta = 0.0
        mint_amount = 0
        burn_amount = 0

        low_target, high_target = self.target_band

        if inflation > high_target:
            # Overheating / inflation high -> Hike interest rate & contract money supply
            rate_delta = min(self.max_rate_change_daily, (inflation - high_target) * 0.1)
            burn_target = int(min(self.max_daily_burn, (inflation - high_target) * 1000))
            cb_balance = world.ledger.balance(CENTRAL_BANK, Asset.COIN)
            burn_amount = min(cb_balance, burn_target)
            if burn_amount > 0:
                world.ledger.burn(
                    CENTRAL_BANK,
                    burn_amount,
                    tick=world.tick,
                    reason="monetary_contraction_inflation_curb",
                )
        elif inflation < low_target or broke_share > 0.25:
            # Liquidity crunch / deflation -> Cut interest rate & inject liquidity
            rate_delta = -min(
                self.max_rate_change_daily, max(low_target - inflation, broke_share) * 0.1
            )
            mint_amount = int(min(self.max_daily_mint, max(50, broke_share * 400)))
            world.ledger.mint(
                CENTRAL_BANK,
                mint_amount,
                tick=world.tick,
                reason="quantitative_easing_stimulus",
            )

        # Apply rate delta with bounds [0.01, 0.25] (1% to 25%)
        new_rate = max(0.01, min(0.25, self.policy_rate + rate_delta))
        self.policy_rate = round(new_rate, 4)

        # Record monetary policy evidence
        ev = Evidence(
            tick=world.tick,
            kind="monetary_policy",
            subject=CENTRAL_BANK,
            metric="policy_rate",
            value=self.policy_rate,
            baseline=inflation,
            threshold=self.target_inflation,
        )
        return ev

    def borrow_discount_window(self, world: World, guild_id: str, amount: int) -> int:
        """Guild emergency liquidity borrowing via discount window (M20.5).

        Borrows at policy_rate + penalty_spread.
        """
        g_acct = f"guild:{guild_id}"
        cb_balance = world.ledger.balance(CENTRAL_BANK, Asset.COIN)
        if cb_balance < amount:
            # Mint emergency liquidity if central bank balance is insufficient
            world.ledger.mint(
                CENTRAL_BANK,
                amount - cb_balance,
                tick=world.tick,
                reason=f"discount_window_emergency_liquidity_{guild_id}",
            )

        world.ledger.transfer(
            CENTRAL_BANK,
            g_acct,
            Asset.COIN,
            amount,
            tick=world.tick,
            reason=f"discount_window_loan_{guild_id}",
        )
        return amount

    def lobby_nudge(
        self, world: World, guild_id: str, direction: str, player: str = "player"
    ) -> bool:
        """Lobby action (M20.6): spends 10 guild reputation to nudge target inflation by +-0.5%."""
        guild = world.guilds.get(guild_id)
        if not guild:
            return False

        current_rep = guild.reputation.get(player, 0)
        if current_rep < 10:
            return False

        guild.reputation[player] -= 10
        if direction == "dovish":
            # Expand target inflation
            self.target_inflation = min(0.05, self.target_inflation + 0.005)
            self.target_band = (self.target_band[0] + 0.005, self.target_band[1] + 0.005)
        elif direction == "hawkish":
            # Contract target inflation
            self.target_inflation = max(0.005, self.target_inflation - 0.005)
            self.target_band = (
                max(0.0, self.target_band[0] - 0.005),
                max(0.01, self.target_band[1] - 0.005),
            )
        return True
