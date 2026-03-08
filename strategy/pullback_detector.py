# strategy/pullback_detector.py

from typing import Optional, Dict, List

from strategy.sr_levels import compute_sr_levels, get_nearest_sr
from strategy.volume_filter import analyze_volume
from strategy.volatility_filter import compute_atr, analyze_volatility


def detect_rejection(open_p, high, low, close):

    body = abs(close - open_p)
    total_range = max(high - low, 1e-9)

    upper_wick = high - max(close, open_p)
    lower_wick = min(close, open_p) - low

    upper_ratio = upper_wick / total_range
    lower_ratio = lower_wick / total_range
    body_ratio = body / total_range

    if lower_ratio > 0.35 and lower_ratio > body_ratio * 1.2:
        return "BULLISH"

    if upper_ratio > 0.35 and upper_ratio > body_ratio * 1.2:
        return "BEARISH"

    return None


def detect_pullback_signal(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float],
    htf_direction: str,
    max_proximity: float = 0.06,
    min_bars: int = 30
) -> Optional[Dict]:

    if len(closes) < min_bars:
        return None

    price = closes[-1]

    # ===============================
    # SR LOCATION
    # ===============================

    sr = compute_sr_levels(highs, lows)

    nearest = get_nearest_sr(price, sr, max_search_pct=max_proximity)

    if not nearest:
        return None

    # ===============================
    # DIRECTION
    # ===============================

    if nearest["type"] == "support":
        direction = "LONG"

    elif nearest["type"] == "resistance":
        direction = "SHORT"

    else:
        return None

    # ===============================
    # HTF ALIGNMENT (soft)
    # ===============================

    htf_score = 0.4

    if direction == "LONG" and htf_direction == "BULLISH":
        htf_score = 1.0

    elif direction == "SHORT" and htf_direction == "BEARISH":
        htf_score = 1.0

    # ===============================
    # EXTENSION FILTER
    # ===============================

    atr = compute_atr(highs, lows, closes)

    if atr:

        recent_swing = abs(closes[-1] - closes[-6])

        if recent_swing > atr * 3:
            return None

    # ===============================
    # VOLATILITY
    # ===============================

    volat_ctx = analyze_volatility(highs, lows, closes)

    volatility_score = 1.0 if volat_ctx.state == "NORMAL" else 0.6

    # ===============================
    # REJECTION
    # ===============================

    rejection_type = detect_rejection(
        closes[-2],
        highs[-1],
        lows[-1],
        closes[-1]
    )

    rejection_score = 0

    if direction == "LONG" and rejection_type == "BULLISH":
        rejection_score = 1.0

    if direction == "SHORT" and rejection_type == "BEARISH":
        rejection_score = 1.0

    # ===============================
    # VOLUME
    # ===============================

    vol_ctx = analyze_volume(volumes)

    volume_score = 0.6 if vol_ctx.score >= 0.3 else 0.2

    # ===============================
    # STRUCTURE REACTION
    # ===============================

    reaction_score = 0.4

    if direction == "LONG" and closes[-1] > closes[-2]:
        reaction_score = 0.6

    if direction == "SHORT" and closes[-1] < closes[-2]:
        reaction_score = 0.6

    # ===============================
    # LOCATION SCORE
    # ===============================

    proximity = nearest["dist_pct"]

    location_score = max(
        0.0,
        (max_proximity - proximity) / max_proximity
    )

    location_score *= 2.2

    # ===============================
    # COMPONENTS
    # ===============================

    components = {

        "location": round(location_score, 2),

        "htf": htf_score,

        "rejection": rejection_score,

        "volume": volume_score,

        "volatility": volatility_score,

        "reaction": reaction_score
    }

    total_score = sum(components.values())

    # ===============================
    # CLASSIFICATION
    # ===============================

    if total_score >= 4.4:
        signal = "CONFIRMED"

    elif total_score >= 2.8:
        signal = "POTENTIAL"

    else:
        return None

    return {

        "signal": signal,
        "direction": direction,
        "score": round(total_score, 2),
        "nearest_level": nearest,
        "components": components,

        "context": {

            "volatility": volat_ctx.state,
            "volume": vol_ctx.state,
            "rejection": rejection_type
        },

        "reason": f"{signal}_{direction}"
    }
