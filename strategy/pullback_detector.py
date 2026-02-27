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
    max_proximity: float = 0.02,
    min_bars: int = 30
) -> Optional[Dict]:
    """
    5-MINUTE SR PULLBACK DETECTOR (CORE ENGINE)

    LONG  -> price near SUPPORT + bullish rejection
    SHORT -> price near RESISTANCE + bearish rejection
    """

    if len(closes) < min_bars:
        return None

    price = closes[-1]

    # ==================================================
    # 1️⃣ SR LOCATION
    # ==================================================

    sr = compute_sr_levels(highs, lows, lookback=240)
    nearest = get_nearest_sr(price, sr, max_search_pct=max_proximity)

    if not nearest:
        return None

    # Direction from SR + HTF alignment
    if nearest["type"] == "support" and htf_direction == "BULLISH":
        direction = "LONG"
    elif nearest["type"] == "resistance" and htf_direction == "BEARISH":
        direction = "SHORT"
    else:
        return None

    # ==================================================
    # 2️⃣ EXTENSION FILTER (5m SCALE)
    # ==================================================

    atr = compute_atr(highs, lows, closes)

    if atr:
        recent_swing = abs(closes[-1] - closes[-6])  # ~20min move
        if recent_swing > atr * 2.2:
            return None

    # ==================================================
    # 3️⃣ VOLATILITY QUALITY
    # ==================================================

    volat_ctx = analyze_volatility(
        current_move=closes[-1] - closes[-2],
        atr_value=atr
    )

    if volat_ctx.state in ("CONTRACTING", "EXHAUSTION"):
        return None

    # ==================================================
    # 4️⃣ REJECTION CONFIRMATION (PRIMARY)
    # ==================================================

    rej = rejection_info(
        closes[-2],
        highs[-1],
        lows[-1],
        closes[-1]
    )

    rejection_ok = False

    if direction == "LONG" and rej["rejection_type"] == "BULLISH":
        rejection_ok = True

    if direction == "SHORT" and rej["rejection_type"] == "BEARISH":
        rejection_ok = True

    # ==================================================
    # 5️⃣ VOLUME SUPPORT (SOFTER in 5m)
    # ==================================================

    vol_ctx = analyze_volume(volumes, close_prices=closes)
    volume_ok = vol_ctx.score >= 0.3

    # ==================================================
    # 6️⃣ STRUCTURE REACTION (5m)
    # ==================================================

    reaction_ok = False

    if direction == "LONG" and closes[-1] > closes[-3]:
        reaction_ok = True

    if direction == "SHORT" and closes[-1] < closes[-3]:
        reaction_ok = True

    # ==================================================
    # 7️⃣ LOCATION SCORING
    # ==================================================

    proximity = nearest["dist_pct"]
    location_score = max(0.0, (max_proximity - proximity) / max_proximity)
    location_score *= 2.0

    # ==================================================
    # 8️⃣ FINAL COMPONENTS
    # ==================================================

    components = {
        "location": round(location_score, 2.5),
        "rejection": 1.2 if rejection_ok else 0.0,
        "volume": 0.8 if volume_ok else 0.0,
        "volatility": 1.0 if volat_ctx.state == "EXPANDING" else 0.4,
        "reaction": 0.6 if reaction_ok else 0.0
    }

    total_score = sum(components.values())

    # ==================================================
    # 9️⃣ CLASSIFICATION
    # ==================================================

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
            "volume": vol_ctx.strength,
            "rejection": rej["rejection_type"]
        },
        "reason": f"{signal}_{direction}"
    }
