# strategy/liquidity_filter.py

from dataclasses import dataclass
from typing import List


# =========================
# OUTPUT
# =========================

@dataclass
class LiquidityContext:

    state: str
    score: float
    avg_volume: float
    comment: str


# =========================
# LIQUIDITY ANALYSIS
# =========================

def analyze_liquidity(
    volume_history: List[float],
    lookback: int = 30,
    min_avg_volume: int = 80_000
) -> LiquidityContext:

    """
    Liquidity suitability for Nifty500 equities.
    """

    if not volume_history or len(volume_history) < lookback:

        return LiquidityContext(
            state="ILLIQUID",
            score=-1.0,
            avg_volume=0.0,
            comment="insufficient data"
        )

    recent = volume_history[-lookback:]

    avg_vol = sum(recent) / lookback


    # ======================
    # LIQUIDITY RULES
    # ======================

    if avg_vol < min_avg_volume:

        return LiquidityContext(
            state="ILLIQUID",
            score=-1.0,
            avg_volume=round(avg_vol),
            comment="below liquidity threshold"
        )


    if avg_vol < min_avg_volume * 2.2:

        return LiquidityContext(
            state="TRADABLE",
            score=0.5,
            avg_volume=round(avg_vol),
            comment="adequate liquidity"
        )


    return LiquidityContext(
        state="HIGH_LIQUID",
        score=1.0,
        avg_volume=round(avg_vol),
        comment="high liquidity"
    )


# =========================
# HELPER
# =========================

def is_liquid(
    volume_history: List[float],
    min_avg_volume: int = 80_000
) -> bool:

    ctx = analyze_liquidity(
        volume_history,
        min_avg_volume=min_avg_volume
    )

    return ctx.state != "ILLIQUID"
