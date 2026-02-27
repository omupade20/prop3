from dataclasses import dataclass
from typing import List


@dataclass
class LiquidityContext:
    state: str      # ILLIQUID | TRADABLE | HIGH_LIQUID
    score: float    # -1 .. +1
    avg_volume: float
    comment: str


def analyze_liquidity(
    volume_history: List[float],
    lookback: int = 30,
    min_avg_volume: int = 250_000
) -> LiquidityContext:
    """
    5-minute liquidity suitability for equities.

    ILLIQUID     → avoid
    TRADABLE     → ok
    HIGH_LIQUID  → best
    """

    if not volume_history or len(volume_history) < lookback:
        return LiquidityContext("ILLIQUID", -1.0, 0.0, "insufficient data")

    recent = volume_history[-lookback:]
    avg_vol = sum(recent) / lookback

    # tuned for Nifty-500 5m bars
    if avg_vol < min_avg_volume:
        return LiquidityContext(
            state="ILLIQUID",
            score=-1.0,
            avg_volume=round(avg_vol),
            comment="below liquidity threshold"
        )

    if avg_vol < min_avg_volume * 3:
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


# simple boolean helper
def is_liquid(volume_history: List[float], min_avg_volume: int = 250_000) -> bool:
    ctx = analyze_liquidity(volume_history, min_avg_volume=min_avg_volume)
    return ctx.state != "ILLIQUID"
