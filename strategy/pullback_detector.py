# strategy/pullback_detector.py

from typing import Optional, Dict, List

from strategy.sr_levels import compute_sr_levels, get_nearest_sr
from strategy.volume_filter import analyze_volume
from strategy.volatility_filter import compute_atr, analyze_volatility
from strategy.price_action import rejection_info


def detect_pullback_signal(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float],
    htf_direction: str,
    max_proximity: float = 0.04,
    min_bars: int = 30
) -> Optional[Dict]:

    if len(closes) < min_bars:
        return None

    price = closes[-1]

    # ===============================
    # SR LOCATION
    # ===============================

    sr = compute_sr_levels(highs, lows)

    nearest = get_nearest_sr(
        price,
        sr,
        max_search_pct=max_proximity
    )

    if not nearest:
        return None

    # ===============================
    # DIRECTION
    # ===============================

    direction = None

    if nearest["type"] == "support":
        direction = "LONG"

    elif nearest["type"] == "resistance":
        direction = "SHORT"

    if direction is None:
        return None

    # ===============================
    # HTF ALIGNMENT (soft)
    # ===============================

    htf_score = 0

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

    if volat_ctx.state == "LOW":
        return None

    # ===============================
    # REJECTION
    # ===============================

    rej = rejection_info(
        closes[-2],
        highs[-1],
        lows[-1],
        closes[-1]
    )

    rejection_score = 0

    if direction == "LONG" and rej["rejection_type"] == "BULLISH":
        rejection_score = 1.2

    if direction == "SHORT" and rej["rejection_type"] == "BEARISH":
        rejection_score = 1.2

    # ===============================
    # VOLUME
    # ===============================

    vol_ctx = analyze_volume(volumes)

    volume_score = 0.6 if vol_ctx.score >= 0.3 else 0.2

    # ===============================
    # STRUCTURE REACTION
    # ===============================

    reaction_score = 0

    if direction == "LONG" and closes[-1] > closes[-3]:
        reaction_score = 0.6

    if direction == "SHORT" and closes[-1] < closes[-3]:
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

        "volatility": 1.0 if volat_ctx.state == "NORMAL" else 0.6,

        "reaction": reaction_score
    }

    total_score = sum(components.values())

    # ===============================
    # CLASSIFICATION
    # ===============================

    if total_score >= 4.8:
        signal = "CONFIRMED"

    elif total_score >= 3.2:
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

            "rejection": rej["rejection_type"]
        },

        "reason": f"{signal}_{direction}"
    }
