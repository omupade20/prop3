from dataclasses import dataclass
from typing import Optional, Dict

from strategy.liquidity_filter import analyze_liquidity
from strategy.vwap_filter import VWAPContext


# =========================
# Output Structure
# =========================

@dataclass
class DecisionResult:
    state: str                 # IGNORE | PREPARE_LONG | PREPARE_SHORT | EXECUTE_LONG | EXECUTE_SHORT
    score: float
    direction: Optional[str]
    components: Dict[str, float]
    reason: str


# =========================
# FINAL 5-MINUTE DECISION ENGINE
# =========================

def final_trade_decision(
    inst_key: str,
    closes: list[float],
    volumes: list[float],
    market_regime: str,            # RANGE | TREND | STRONG_TREND
    htf_bias_direction: str,       # BULLISH | BEARISH
    vwap_ctx: VWAPContext,
    pullback_signal: Optional[Dict],
) -> DecisionResult:

    # ==================================================
    # 1️⃣ STRUCTURE (CORE: SR PULLBACK)
    # ==================================================

    if not pullback_signal:
        return DecisionResult("IGNORE", 0.0, None, {}, "no pullback")

    direction = pullback_signal["direction"]
    pb_score = pullback_signal["score"]

    # POTENTIAL → PREPARE only
    if pullback_signal["signal"] == "POTENTIAL":
        return DecisionResult(
            state=f"PREPARE_{direction}",
            score=pb_score,
            direction=direction,
            components={"pullback": pb_score},
            reason="potential pullback"
        )

    # Normalize pullback influence
    score = pb_score * 0.85
    components = {"pullback": round(pb_score * 0.85, 2)}

    # ==================================================
    # 2️⃣ HTF ALIGNMENT
    # ==================================================

    if direction == "LONG" and htf_bias_direction != "BULLISH":
        return DecisionResult("IGNORE", 0.0, None, {}, "htf mismatch")

    if direction == "SHORT" and htf_bias_direction != "BEARISH":
        return DecisionResult("IGNORE", 0.0, None, {}, "htf mismatch")

    score += 1.0
    components["htf"] = 1.0

    # ==================================================
    # 3️⃣ MARKET REGIME (5m)
    # ==================================================

    if market_regime == "RANGE":
        return DecisionResult("IGNORE", 0.0, None, {}, "range regime")

    if market_regime == "TREND":
        score += 0.6
        components["regime"] = 0.6

    elif market_regime == "STRONG_TREND":
        score += 1.0
        components["regime"] = 1.0

    # ==================================================
    # 4️⃣ VWAP ENVIRONMENT
    # ==================================================

    if direction == "LONG" and vwap_ctx.acceptance == "BELOW":
        return DecisionResult("IGNORE", 0.0, None, {}, "below vwap")

    if direction == "SHORT" and vwap_ctx.acceptance == "ABOVE":
        return DecisionResult("IGNORE", 0.0, None, {}, "above vwap")

    vwap_score = max(0.0, vwap_ctx.score * 0.5)
    score += vwap_score
    components["vwap"] = round(vwap_score, 2)

    # ==================================================
    # 5️⃣ LIQUIDITY SAFETY
    # ==================================================

    liq = analyze_liquidity(volumes)

    if liq.score < 0:
        return DecisionResult("IGNORE", 0.0, None, {}, "illiquid")

    liq_score = min(1.0, liq.score * 0.4)
    score += liq_score
    components["liquidity"] = round(liq_score, 2)

    # ==================================================
    # 6️⃣ FINAL CLASSIFICATION
    # ==================================================

    score = round(score, 2)

    if score >= 6.2:
        state = f"EXECUTE_{direction}"
        reason = "confirmed 5m pullback"

    elif score >= 4.6:
        state = f"PREPARE_{direction}"
        reason = "developing 5m pullback"

    else:
        state = "IGNORE"
        reason = "weak setup"

    return DecisionResult(
        state=state,
        score=score,
        direction=direction if state != "IGNORE" else None,
        components=components,
        reason=reason
    )
