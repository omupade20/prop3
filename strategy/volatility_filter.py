# strategy/volatility_filter.py

from dataclasses import dataclass
from typing import List, Optional


def compute_true_range(highs: List[float], lows: List[float], closes: List[float]):

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


def compute_atr(highs, lows, closes, period=14):

    tr = compute_true_range(highs, lows, closes)

    if len(tr) < period:
        return None

    return sum(tr[-period:]) / period


@dataclass
class VolatilityContext:

    state: str
    score: float
    atr: float
    vol_norm: float
    comment: str


def analyze_volatility(highs, lows, closes):

    atr = compute_atr(highs, lows, closes)

    if atr is None or len(closes) < 10:

        return VolatilityContext(
            state="LOW",
            score=-0.3,
            atr=0.0,
            vol_norm=0.0,
            comment="insufficient data"
        )

    avg_price = sum(closes[-10:]) / 10

    vol_norm = atr / avg_price if avg_price > 0 else 0.0

    # ======================
    # IMPROVED THRESHOLDS
    # ======================

    if vol_norm < 0.001:

        return VolatilityContext(
            state="LOW",
            score=-0.2,
            atr=round(atr, 6),
            vol_norm=round(vol_norm, 5),
            comment="low volatility"
        )

    if vol_norm < 0.006:

        return VolatilityContext(
            state="NORMAL",
            score=0.8,
            atr=round(atr, 6),
            vol_norm=round(vol_norm, 5),
            comment="tradable volatility"
        )

    return VolatilityContext(
        state="HIGH",
        score=-0.1,
        atr=round(atr, 6),
        vol_norm=round(vol_norm, 5),
        comment="high volatility"
    )
