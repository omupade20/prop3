# strategy/htf_bias.py

from dataclasses import dataclass
from typing import Optional, List
from strategy.indicators import exponential_moving_average


# ------------------------
# HTF Bias Output
# ------------------------

@dataclass
class HTFBias:
    direction: str     # BULLISH | BEARISH | NEUTRAL
    strength: float    # 0 – 10
    label: str         # BULLISH_STRONG, BULLISH_WEAK, etc.
    comment: str


# ------------------------
# HTF Bias Logic
# ------------------------

def get_htf_bias(
    prices: List[float],
    vwap_value: Optional[float] = None,
    short_period: int = 21,
    long_period: int = 50,
    vwap_tolerance: float = 0.008
) -> HTFBias:

    """
    Compute higher timeframe directional bias.

    Uses:
    - EMA crossover
    - structural strength
    - VWAP context

    Returns:
    HTFBias(direction, strength, label, comment)
    """

    if not prices:
        return HTFBias("NEUTRAL", 0.5, "NEUTRAL", "No price data")

    min_required = long_period + 3

    if len(prices) < min_required:
        return HTFBias("NEUTRAL", 0.5, "NEUTRAL", "Insufficient HTF data")

    ema_short = exponential_moving_average(prices, short_period)
    ema_long = exponential_moving_average(prices, long_period)

    if ema_short is None or ema_long is None:
        return HTFBias("NEUTRAL", 0.5, "NEUTRAL", "EMA unavailable")

    price = prices[-1]

    # ------------------------
    # Direction
    # ------------------------

    ema_diff = ema_short - ema_long

    if ema_diff > 0:
        direction = "BULLISH"
    elif ema_diff < 0:
        direction = "BEARISH"
    else:
        return HTFBias("NEUTRAL", 1.0, "NEUTRAL", "Flat EMA")

    # ------------------------
    # Strength calculation
    # ------------------------

    recent_slice = prices[-20:]
    recent_range = max(recent_slice) - min(recent_slice)

    if recent_range <= 0:
        base_strength = 1.0
    else:
        base_strength = min(abs(ema_diff) / recent_range * 8.0, 6.0)

    strength = base_strength

    comment_parts = ["EMA alignment"]

    # ------------------------
    # Trend persistence
    # ------------------------

    if len(prices) > long_period + 5:

        past_prices = prices[:-5]

        past_ema_short = exponential_moving_average(past_prices, short_period)
        past_ema_long = exponential_moving_average(past_prices, long_period)

        if past_ema_short and past_ema_long:

            past_diff = past_ema_short - past_ema_long

            if (direction == "BULLISH" and past_diff > 0) or (
                direction == "BEARISH" and past_diff < 0
            ):
                strength += 0.8
                comment_parts.append("Trend persistence")

    # ------------------------
    # VWAP Context
    # ------------------------

    if vwap_value and vwap_value > 0:

        dist = (price - vwap_value) / vwap_value

        if direction == "BULLISH":

            if dist > vwap_tolerance:
                strength += 0.8
                comment_parts.append("Above VWAP")

            elif dist < -vwap_tolerance:
                strength -= 0.6
                comment_parts.append("Below VWAP pressure")

            else:
                comment_parts.append("Near VWAP")

        else:

            if dist < -vwap_tolerance:
                strength += 0.8
                comment_parts.append("Below VWAP")

            elif dist > vwap_tolerance:
                strength -= 0.6
                comment_parts.append("Above VWAP pressure")

            else:
                comment_parts.append("Near VWAP")

    # ------------------------
    # Clamp strength
    # ------------------------

    strength = max(0.5, min(round(strength, 2), 10.0))

    # ------------------------
    # Label
    # ------------------------

    if direction == "BULLISH":
        label = "BULLISH_STRONG" if strength >= 6 else "BULLISH_WEAK"
    else:
        label = "BEARISH_STRONG" if strength >= 6 else "BEARISH_WEAK"

    return HTFBias(
        direction=direction,
        strength=strength,
        label=label,
        comment=" | ".join(comment_parts)
    )
