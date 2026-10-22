"""Smuggling faction and contraband black market operations (M19.1 & M19.2).

When prices hit their ceiling or bandits cut the roads for 3+ consecutive days,
the Smuggler faction activates:
- Sells contraband directly from ``outside`` stock at 1.5x spot price to NPCs
  with unfilled demand.
- Bypasses market tax and transport capacity limits.
- Seeded probability of interception by town guards. Confiscated shipments are
  transferred to the town's stockpile.
- Tracks smuggled volume and lost tax revenue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from questless.sim.entities import OUTSIDE, TOWN, Asset

if TYPE_CHECKING:
    from questless.sim.world import World

SMUGGLERS = "smugglers"
PREMIUM_MULTIPLIER = 1.50


@dataclass
class SmugglingFaction:
    """Manages smuggler activation state, triggers, and contraband trade."""

    active: bool = False
    active_since_tick: int | None = None
    trigger_reason: str = ""
    consecutive_stress_days: int = 0
    total_smuggled_volume: int = 0
    total_lost_tax: int = 0
    total_confiscated_volume: int = 0
    evidence: dict[str, Any] = field(default_factory=dict)

    def check_trigger(self, world: World) -> bool:
        """Check if conditions hold for 3+ consecutive days to activate smugglers."""
        stress_detected = False
        reasons = []

        # Condition 1: Price at ceiling for any good
        for good, price in world.prices.items():
            base = world.config.goods[good].base_price
            ceil = base * world.config.goods[good].price_ceiling
            if price >= ceil:
                stress_detected = True
                reasons.append(f"Price ceiling reached for {good.value} ({price} >= {ceil})")

        # Condition 2: Transport shock active and transport backlog exceeds threshold
        transport_shock_active = any(
            s.effect.value == "transport_capacity" and s.start <= world.tick < s.end
            for s in world.modifiers.shocks
        )
        if transport_shock_active:
            backlog = sum(
                world.ledger.balance(site_acc, good)
                for npc in world.npcs.values()
                for site_acc in [npc.site_account]
                for good in world.config.goods
                if site_acc != npc.account
            )
            if backlog > 20:
                stress_detected = True
                reasons.append(f"Transport shock active with backlog {backlog} units")

        if stress_detected:
            self.consecutive_stress_days += 1
            if self.consecutive_stress_days >= 3 and not self.active:
                self.active = True
                self.active_since_tick = world.tick
                self.trigger_reason = "; ".join(reasons)
                self.evidence = {
                    "activated_tick": world.tick,
                    "reasons": reasons,
                    "consecutive_days": self.consecutive_stress_days,
                }
        else:
            self.consecutive_stress_days = 0

        return self.active

    def run_contraband_trade(self, world: World) -> dict[str, int]:
        """Execute contraband trade in a tick slot after market clearing."""
        if not self.active:
            return {"smuggled": 0, "lost_tax": 0, "confiscated": 0}

        rng = world.rng.stream("smuggling")
        tax_rate = world.config.town.market_tax
        smuggled_today = 0
        tax_lost_today = 0
        confiscated_today = 0

        # Guard strength determines interception probability
        guards = [n for n in world.npcs.values() if n.profession.value == "guard"]
        interception_chance = min(0.40, len(guards) * 0.05)

        # NPCs with unmet demand from today's market
        latest_stats = world.stats[-1] if world.stats else None
        if not latest_stats:
            return {"smuggled": 0, "lost_tax": 0, "confiscated": 0}

        for npc in world.npcs_in_order():
            for good, unmet_qty in list(latest_stats.unmet.items()):
                if unmet_qty <= 0:
                    continue

                outside_avail = world.ledger.balance(OUTSIDE, good)
                if outside_avail <= 0:
                    continue

                spot = world.unit_price(good)
                contraband_price = int(round(spot * PREMIUM_MULTIPLIER))
                npc_coin = world.ledger.balance(npc.account, Asset.COIN)
                affordable = npc_coin // max(1, contraband_price)
                shipment_qty = min(unmet_qty, outside_avail, affordable, 5)

                if shipment_qty <= 0:
                    continue

                cost = shipment_qty * contraband_price
                theoretical_tax = int(round(cost * tax_rate))

                # Check interception
                if rng.random() < interception_chance:
                    # Confiscate shipment to town account
                    world.ledger.transfer(
                        OUTSIDE,
                        TOWN,
                        good,
                        shipment_qty,
                        tick=world.tick,
                        reason="contraband_confiscated",
                    )
                    confiscated_today += shipment_qty
                else:
                    # Successful delivery to NPC
                    world.ledger.transfer(
                        OUTSIDE,
                        npc.account,
                        good,
                        shipment_qty,
                        tick=world.tick,
                        reason="contraband_delivery",
                    )
                    world.ledger.transfer(
                        npc.account,
                        SMUGGLERS,
                        Asset.COIN,
                        cost,
                        tick=world.tick,
                        reason="contraband_payment",
                    )
                    smuggled_today += shipment_qty
                    tax_lost_today += theoretical_tax
                    latest_stats.unmet[good] = max(0, unmet_qty - shipment_qty)

        self.total_smuggled_volume += smuggled_today
        self.total_lost_tax += tax_lost_today
        self.total_confiscated_volume += confiscated_today

        # Record on TickStats for M19.3 lawlessness index
        if latest_stats:
            latest_stats.smuggled_volume = smuggled_today
            latest_stats.lost_tax = tax_lost_today

        return {
            "smuggled": smuggled_today,
            "lost_tax": tax_lost_today,
            "confiscated": confiscated_today,
        }
