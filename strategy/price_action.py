# strategy/price_action.py

from typing import List, Dict


# =========================
# Rejection Analysis (5m)
# =========================

def rejection_info(open_p: float, high: float, low: float, close: float) -> Dict:
    """
    5-minute rejection analysis.

    Detects:
      - bullish rejection (long lower wick)
      - bearish rejection (long upper wick)
    """

    body = abs(close - open_p)

    total_range = max(high - low, 1e-9)

    upper_wick = max(0.0, high - max(close, open_p))
    lower_wick = max(0.0, min(close, open_p) - low)

    upper_rel = upper_wick / total_range
    lower_rel = lower_wick / total_range
    body_rel = body / total_range

    rejection_type = None
    rejection_score = 0.0

    # =========================
    # Bullish rejection
    # =========================

    if lower_rel > 0.28 and lower_rel > body_rel * 1.05:

        rejection_type = "BULLISH"

        rejection_score = min(1.0, (lower_rel - 0.28) / 0.45)

    # =========================
    # Bearish rejection
    # =========================

    elif upper_rel > 0.28 and upper_rel > body_rel * 1.05:

        rejection_type = "BEARISH"

        rejection_score = min(1.0, (upper_rel - 0.28) / 0.45)

    return {
        "rejection_type": rejection_type,
        "rejection_score": round(rejection_score, 3),
        "upper_wick": round(upper_wick, 6),
        "lower_wick": round(lower_wick, 6),
        "body": round(body, 6),
        "range": round(total_range, 6)
    }


# =========================
# Price Action Context (5m)
# =========================

def price_action_context(
    highs: List[float],
    lows: List[float],
    opens: List[float],
    closes: List[float],
) -> Dict:

    """
    Interpret rejection strength from last candle.
    """

    if not highs or not lows or not opens or not closes:

        return {
            "rejection_type": None,
            "rejection_score": 0.0,
            "score": 0.0,
            "comment": "no data"
        }

    rej = rejection_info(
        opens[-1],
        highs[-1],
        lows[-1],
        closes[-1]
    )

    score = 0.0

    comment = "no rejection"

    if rej["rejection_type"] == "BULLISH":

        score = rej["rejection_score"]

        comment = "bullish rejection"

    elif rej["rejection_type"] == "BEARISH":

        score = -rej["rejection_score"]

        comment = "bearish rejection"

    return {
        "rejection_type": rej["rejection_type"],
        "rejection_score": rej["rejection_score"],
        "score": round(score, 3),
        "comment": comment
    }
