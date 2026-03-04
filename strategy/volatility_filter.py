# strategy/volatility_filter.py

from dataclasses import dataclass
from typing import List, Optional


# =========================
# TRUE RANGE
# =========================

def compute_true_range(highs: List[float], lows: List[float], closes: List[float]) -> List[float]:

    if len(highs) < 2:
        return []

    tr = []

    for i in range(1, len(highs)):

        tr.append(
            max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )
        )

    return tr


# =========================
# ATR
# =========================

def compute_atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14
) -> Optional[float]:

    tr = compute_true_range(highs, lows, closes)

    if len(tr) < period:
        return None

    return sum(tr[-period:]) / period


# =========================
# VOLATILITY OUTPUT
# =========================

@dataclass
class VolatilityContext:

    state: str      # LOW | NORMAL | HIGH
    score: float    # -1 .. +1
    atr: float
    vol_norm: float
    comment: str


# =========================
# VOLATILITY ANALYSIS
# =========================

def analyze_volatility(
    highs: List[float],
    lows: List[float],
    closes: List[float]
) -> VolatilityContext:

    """
    Intraday volatility suitability.
    """

    atr = compute_atr(highs, lows, closes)

    if atr is None or len(closes) < 10:

        return VolatilityContext(
            state="LOW",
            score=-0.5,
            atr=0.0,
            vol_norm=0.0,
            comment="insufficient data"
        )

    avg_price = sum(closes[-10:]) / 10

    vol_norm = atr / avg_price if avg_price > 0 else 0.0

    # ======================
    # VOLATILITY RULES
    # ======================

    if vol_norm < 0.0014:

        return VolatilityContext(
            state="LOW",
            score=-0.4,
            atr=round(atr, 6),
            vol_norm=round(vol_norm, 5),
            comment="low volatility"
        )

    if vol_norm < 0.005:

        return VolatilityContext(
            state="NORMAL",
            score=0.8,
            atr=round(atr, 6),
            vol_norm=round(vol_norm, 5),
            comment="tradable volatility"
        )

    return VolatilityContext(
        state="HIGH",
        score=-0.2,
        atr=round(atr, 6),
        vol_norm=round(vol_norm, 5),
        comment="high volatility"
    )
