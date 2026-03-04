from dataclasses import dataclass
from typing import Optional, Dict

from strategy.liquidity_filter import analyze_liquidity
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
# FINAL DECISION ENGINE
# =========================

def final_trade_decision(
    inst_key: str,
    closes: list[float],
    volumes: list[float],
    market_regime: str,
    htf_bias_direction: str,
    vwap_ctx: VWAPContext,
    pullback_signal: Optional[Dict],
) -> DecisionResult:

    # ==================================================
    # 1️⃣ CORE STRUCTURE
    # ==================================================

    if not pullback_signal:
        return DecisionResult("IGNORE", 0.0, None, {}, "no pullback")

    direction = pullback_signal["direction"]
    pb_score = pullback_signal["score"]

    # POTENTIAL → PREPARE
    if pullback_signal["signal"] == "POTENTIAL":

        return DecisionResult(
            state=f"PREPARE_{direction}",
            score=pb_score,
            direction=direction,
            components={"pullback": pb_score},
            reason="potential pullback"
        )

    # Base score
    score = pb_score * 0.9

    components = {
        "pullback": round(pb_score * 0.9, 2)
    }

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
    # 3️⃣ MARKET REGIME
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
    # 4️⃣ VWAP CONTEXT (soft filter)
    # ==================================================

    vwap_score = vwap_ctx.score * 0.4

    score += vwap_score

    components["vwap"] = round(vwap_score, 2)

    # ==================================================
    # 5️⃣ LIQUIDITY
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

    if score >= 5.0:

        state = f"EXECUTE_{direction}"
        reason = "confirmed pullback"

    elif score >= 3.8:

        state = f"PREPARE_{direction}"
        reason = "developing pullback"

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
