from dataclasses import dataclass
from typing import Optional, Dict

from strategy.volume_filter import analyze_volume
from strategy.volatility_filter import analyze_volatility, compute_atr
from strategy.liquidity_filter import analyze_liquidity
from strategy.price_action import price_action_context
from strategy.sr_levels import sr_location_score
from strategy.vwap_filter import VWAPContext


# =========================
# Output Structure
# =========================

@dataclass
class DecisionResult:
    state: str
    score: float
    direction: Optional[str]
    components: Dict[str, float]
    reason: str


# =========================
# CONTINUATION PULLBACK ENGINE
# =========================

def final_trade_decision(
    inst_key: str,
    prices: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    market_regime: str,
    htf_bias_direction: str,
    vwap_ctx: VWAPContext,
    pullback_signal: Optional[Dict],
) -> DecisionResult:

    if not pullback_signal:
        return DecisionResult("IGNORE", 0.0, None, {}, "no pullback")

    direction = pullback_signal["direction"]

    components: Dict[str, float] = {}
    score = 0.0

    # ==================================================
    # 1️⃣ STRUCTURE (Continuation priority)
    # ==================================================

    components["structure"] = 3.8
    score += 3.8

    # ==================================================
    # 2️⃣ HTF ALIGNMENT
    # ==================================================

    if direction == "LONG" and htf_bias_direction != "BULLISH":
        return DecisionResult("IGNORE", 0.0, None, {}, "htf mismatch")

    if direction == "SHORT" and htf_bias_direction != "BEARISH":
        return DecisionResult("IGNORE", 0.0, None, {}, "htf mismatch")

    components["htf"] = 1.6
    score += 1.6

    # ==================================================
    # 3️⃣ MARKET REGIME
    # ==================================================

    if market_regime in ("WEAK", "COMPRESSION"):
        return DecisionResult("IGNORE", 0.0, None, {}, "bad regime")

    if market_regime == "EARLY_TREND":
        components["regime"] = 1.2
        score += 1.2
    elif market_regime == "TRENDING":
        components["regime"] = 1.6
        score += 1.6

    # ==================================================
    # 4️⃣ VWAP CONTEXT
    # ==================================================

    if direction == "LONG" and vwap_ctx.acceptance == "BELOW":
        return DecisionResult("IGNORE", 0.0, None, {}, "below vwap")

    if direction == "SHORT" and vwap_ctx.acceptance == "ABOVE":
        return DecisionResult("IGNORE", 0.0, None, {}, "above vwap")

    components["vwap"] = vwap_ctx.score
    score += vwap_ctx.score

    # ==================================================
    # 5️⃣ VOLUME
    # ==================================================

    vol_ctx = analyze_volume(volumes, close_prices=closes)

    if vol_ctx.score < 0.4:
        return DecisionResult("IGNORE", 0.0, None, {}, "weak volume")

    components["volume"] = vol_ctx.score
    score += vol_ctx.score

    # ==================================================
    # 6️⃣ VOLATILITY
    # ==================================================

    atr = compute_atr(highs, lows, closes)
    move = closes[-1] - closes[-2] if len(closes) > 1 else 0.0

    volat_ctx = analyze_volatility(move, atr)

    if volat_ctx.state in ["CONTRACTING", "EXHAUSTION"]:
        return DecisionResult("IGNORE", 0.0, None, {}, "bad volatility")

    components["volatility"] = volat_ctx.score
    score += volat_ctx.score

    # ==================================================
    # 7️⃣ LIQUIDITY
    # ==================================================

    liq_ctx = analyze_liquidity(volumes)

    if liq_ctx.score < 0:
        return DecisionResult("IGNORE", 0.0, None, {}, "illiquid")

    components["liquidity"] = liq_ctx.score
    score += liq_ctx.score

    # ==================================================
    # 8️⃣ PRICE ACTION
    # ==================================================

    pa_ctx = price_action_context(
        prices=closes,
        highs=highs,
        lows=lows,
        opens=closes,
        closes=closes
    )

    components["price_action"] = pa_ctx["score"]
    score += pa_ctx["score"]

    # ==================================================
    # 9️⃣ SR LOCATION (5m)
    # ==================================================

    nearest = pullback_signal.get("nearest_level")

    sr_score = sr_location_score(closes[-1], nearest, direction)

    components["sr"] = sr_score
    score += sr_score * 1.4

    # ==================================================
    # 🔟 FINAL DECISION
    # ==================================================

    score = round(max(min(score, 10.0), 0.0), 2)

    if score >= 6.2:
        state = f"EXECUTE_{direction}"
        reason = "continuation pullback"

    elif score >= 4.8:
        state = f"PREPARE_{direction}"
        reason = "developing continuation"

    else:
        state = "IGNORE"
        reason = "low edge"

    return DecisionResult(
        state=state,
        score=score,
        direction=direction if state != "IGNORE" else None,
        components=components,
        reason=reason
    )
