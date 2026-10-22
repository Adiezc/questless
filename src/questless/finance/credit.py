"""Credit scoring model for Questless economic entities (M17.5).

Computes deterministic credit scores (300 to 850 scale) from:
- Repayment history (on-time settlement share vs defaults)
- Current debt-to-income or debt-to-treasury ratio
- History length (tenure in ticks)

Strictly deterministic with zero RNG.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from questless.finance.obligations import ObligationStatus

if TYPE_CHECKING:
    from questless.finance.obligations import ObligationRegistry


def score(
    entity_id: str,
    registry: ObligationRegistry,
    annual_income: int = 100,
    current_tick: int = 0,
) -> int:
    """Calculate deterministic credit score between 300 and 850."""
    # Retrieve all obligations involving entity as debtor
    debts = [ob for ob in registry.obligations.values() if ob.debtor == entity_id]

    # Baseline score for new borrowers with zero history
    if not debts:
        return 650

    settled_count = sum(1 for ob in debts if ob.status == ObligationStatus.SETTLED)
    default_count = sum(1 for ob in debts if ob.status == ObligationStatus.DEFAULTED)
    active_debts = [ob for ob in debts if ob.status == ObligationStatus.ACTIVE]

    total_closed = settled_count + default_count

    # Repayment history factor (-200 to +120 points)
    if total_closed > 0:
        on_time_ratio = settled_count / total_closed
        history_delta = int((on_time_ratio * 120) - (default_count * 150))
    else:
        history_delta = 0

    # Current debt burden factor
    current_outstanding = sum(ob.remaining_due() for ob in active_debts)
    income = max(1, annual_income)
    dti = current_outstanding / income

    if dti <= 0.2:
        burden_delta = 50
    elif dti <= 0.5:
        burden_delta = 20
    elif dti <= 1.0:
        burden_delta = -30
    elif dti <= 2.0:
        burden_delta = -80
    else:
        burden_delta = -150

    # History tenure factor
    oldest_tick = min((ob.created_tick for ob in debts), default=current_tick)
    tenure_days = max(0, current_tick - oldest_tick)
    tenure_bonus = min(30, tenure_days // 10)

    # Base: 650
    raw_score = 650 + history_delta + burden_delta + tenure_bonus

    # Clamp to standard 300-850 range
    return max(300, min(850, raw_score))
