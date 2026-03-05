# strategy/market_regime.py

from typing import List, Optional
from dataclasses import dataclass


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


def compute_adx(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14
) -> Optional[float]:

    if len(highs) < period + 2:
        return None

    plus_dm = []
    minus_dm = []

    for i in range(1, len(highs)):

        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]

        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0)

    atr = compute_atr(highs, lows, closes, period)

    if atr is None or atr == 0:
        return None

    plus_di = (sum(plus_dm[-period:]) / atr) * 100
    minus_di = (sum(minus_dm[-period:]) / atr) * 100

    if plus_di + minus_di == 0:
        return 0.0

    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100

    return dx


@dataclass
class MarketRegime:

    state: str
    strength: float
    atr: float
    adx: float
    comment: str


def detect_market_regime(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    min_bars: int = 25
) -> MarketRegime:

    if len(highs) < min_bars:

        return MarketRegime(
            state="RANGE",
            strength=0.5,
            atr=0.0,
            adx=0.0,
            comment="insufficient data"
        )

    atr = compute_atr(highs, lows, closes)
    adx = compute_adx(highs, lows, closes)

    if atr is None or adx is None:

        return MarketRegime(
            state="RANGE",
            strength=0.5,
            atr=0.0,
            adx=0.0,
            comment="indicators unavailable"
        )

    window = min(20, len(closes))

    avg_price = sum(closes[-window:]) / window

    vol_norm = atr / avg_price if avg_price > 0 else 0.0

    # ======================
    # REGIME LOGIC
    # ======================

    if adx >= 22 and vol_norm > 0.002:

        strength = min(10.0, 6 + (adx - 22) * 0.25)

        return MarketRegime(
            state="STRONG_TREND",
            strength=round(strength, 2),
            atr=round(atr, 6),
            adx=round(adx, 2),
            comment="strong trend"
        )

    if adx >= 14 and vol_norm > 0.0013:

        strength = min(10.0, 4 + (adx - 14) * 0.3)

        return MarketRegime(
            state="TREND",
            strength=round(strength, 2),
            atr=round(atr, 6),
            adx=round(adx, 2),
            comment="tradable trend"
        )

    strength = max(0.5, adx * 0.06)

    return MarketRegime(
        state="RANGE",
        strength=round(strength, 2),
        atr=round(atr, 6),
        adx=round(adx, 2),
        comment="range / chop"
    )
