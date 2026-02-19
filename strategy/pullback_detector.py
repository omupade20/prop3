from typing import Optional, Dict, List
from strategy.sr_levels import compute_sr_levels, get_nearest_sr
from strategy.volume_filter import analyze_volume
from strategy.volatility_filter import compute_atr, analyze_volatility
from strategy.price_action import rejection_info


def detect_pullback_signal(
    prices_1m: List[float],
    highs_1m: List[float],
    lows_1m: List[float],
    closes_1m: List[float],
    volumes_1m: List[float],
    highs_5m: List[float],
    lows_5m: List[float],
    htf_direction: str,
    max_proximity: float = 0.025,
    min_bars: int = 40
) -> Optional[Dict]:
    """
    CONTINUATION PULLBACK DETECTOR (5m structure + 1m entry)

    Structure:
        - 5m SR defines macro level
        - 1m defines timing
        - Requires shallow pullback + resume
    """

    if len(closes_1m) < min_bars or len(highs_5m) < 20:
        return None

    last_price = closes_1m[-1]

    # ==================================================
    # 1️⃣ 5m STRUCTURE LOCATION
    # ==================================================

    sr_5m = compute_sr_levels(highs_5m, lows_5m)
    nearest = get_nearest_sr(last_price, sr_5m, max_search_pct=max_proximity)

    if not nearest:
        return None

    trade_direction = None

    if nearest["type"] == "support" and htf_direction == "BULLISH":
        trade_direction = "LONG"

    elif nearest["type"] == "resistance" and htf_direction == "BEARISH":
        trade_direction = "SHORT"

    else:
        return None

    # ==================================================
    # 2️⃣ SHALLOW PULLBACK REQUIREMENT (Continuation logic)
    # ==================================================

    recent_leg = abs(closes_1m[-1] - closes_1m[-8])
    atr = compute_atr(highs_1m, lows_1m, closes_1m)

    if not atr or atr <= 0:
        return None

    # Must NOT be extended
    if recent_leg > atr * 1.4:
        return None

    # ==================================================
    # 3️⃣ 1m PRICE REJECTION AT LEVEL
    # ==================================================

    last_rej = rejection_info(
        closes_1m[-2],
        highs_1m[-1],
        lows_1m[-1],
        closes_1m[-1]
    )

    rejection_ok = False

    if trade_direction == "LONG" and last_rej["rejection_type"] == "BULLISH":
        rejection_ok = True

    if trade_direction == "SHORT" and last_rej["rejection_type"] == "BEARISH":
        rejection_ok = True

    # Require some directional resume
    resume_ok = False
    if trade_direction == "LONG" and closes_1m[-1] > closes_1m[-3]:
        resume_ok = True
    if trade_direction == "SHORT" and closes_1m[-1] < closes_1m[-3]:
        resume_ok = True

    if not (rejection_ok or resume_ok):
        return None

    # ==================================================
    # 4️⃣ VOLUME CONFIRMATION (Stricter)
    # ==================================================

    vol_ctx = analyze_volume(volumes_1m, close_prices=closes_1m)

    if vol_ctx.score < 0.8:
        return None

    # ==================================================
    # 5️⃣ VOLATILITY PHASE FILTER
    # ==================================================

    volat_ctx = analyze_volatility(
        current_move=closes_1m[-1] - closes_1m[-2],
        atr_value=atr
    )

    if volat_ctx.state not in ["BUILDING", "EXPANDING"]:
        return None

    # ==================================================
    # 6️⃣ CONFIDENCE SCORING (More Selective)
    # ==================================================

    components = {
        "location": 0.0,
        "rejection": 0.0,
        "volume": 0.0,
        "volatility": 0.0
    }

    # Stronger proximity weighting
    proximity_score = max(0, (max_proximity - nearest["dist_pct"]) * 80)
    components["location"] = min(proximity_score, 3.0)

    if rejection_ok:
        components["rejection"] = 2.0

    components["volume"] = min(vol_ctx.score, 2.0)
    components["volatility"] = min(volat_ctx.score, 1.5)

    total_score = sum(components.values())

    if total_score < 5.5:
        return None

    return {
        "signal": "CONFIRMED",
        "direction": trade_direction,
        "score": round(total_score, 2),
        "nearest_level": nearest,
        "components": components,
        "context": {
            "volatility": volat_ctx.state,
            "volume": vol_ctx.strength,
            "rejection": last_rej["rejection_type"]
        },
        "reason": f"CONTINUATION_PULLBACK_{trade_direction}"
    }
