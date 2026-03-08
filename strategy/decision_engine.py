# strategy/decision_engine.py

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class DecisionResult:
    state: str
    score: float
    direction: Optional[str]
    components: Dict[str, float]
    reason: str


def final_trade_decision(
    inst_key: str,
    closes: list[float],
    volumes: list[float],
    market_regime: str,
    htf_bias_direction: str,
    pullback_signal: Optional[Dict],
) -> DecisionResult:

    # ==================================================
    # 1️⃣ CORE STRUCTURE
    # ==================================================

    if not pullback_signal:
        return DecisionResult("IGNORE", 0.0, None, {}, "no pullback")

    direction = pullback_signal["direction"]
    pb_score = pullback_signal["score"]

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
    # 4️⃣ FINAL CLASSIFICATION
    # ==================================================

    score = round(score, 2)

    if score >= 4.5:

        state = f"EXECUTE_{direction}"
        reason = "confirmed pullback"

    elif score >= 3.0:

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
