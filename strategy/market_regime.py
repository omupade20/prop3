from typing import List, Optional
from dataclasses import dataclass


# =========================
# Core Calculations
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


def compute_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
    tr = compute_true_range(highs, lows, closes)
    if len(tr) < period:
        return None
    return sum(tr[-period:]) / period


def compute_adx(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
    if len(highs) < period + 1:
        return None

    plus_dm, minus_dm = [], []

    for i in range(1, len(highs)):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]

        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)

    atr = compute_atr(highs, lows, closes, period)
    if atr is None or atr == 0:
        return None

    plus_di = (sum(plus_dm[-period:]) / atr) * 100
    minus_di = (sum(minus_dm[-period:]) / atr) * 100

    if plus_di + minus_di == 0:
        return 0.0

    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100
    return dx


# =========================
# Regime Output
# =========================

@dataclass
class MarketRegime:
    state: str        # RANGE | TREND | STRONG_TREND
    strength: float   # 0 – 10
    atr: float
    adx: float
    comment: str


# =========================
# 5m Regime Detection
# =========================

def detect_market_regime(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    min_bars: int = 25
) -> MarketRegime:
    """
    5-minute trend suitability detector.

    Purpose:
    - Decide if pullbacks are tradable
    - Filter chop
    """

    if len(highs) < min_bars:
        return MarketRegime("RANGE", 0.5, 0.0, 0.0, "insufficient data")

    atr = compute_atr(highs, lows, closes)
    adx = compute_adx(highs, lows, closes)

    if atr is None or adx is None:
        return MarketRegime("RANGE", 0.5, 0.0, 0.0, "indicators unavailable")

    # normalized volatility
    avg_price = sum(closes[-24:]) / min(24, len(closes))
    vol_norm = atr / avg_price if avg_price > 0 else 0.0

    # =====================
    # REGIME RULES (5m)
    # =====================

    # strong trend
    if adx >= 28 and vol_norm > 0.004:
        strength = min(10.0, 6 + (adx - 28) * 0.15)
        return MarketRegime(
            state="STRONG_TREND",
            strength=round(strength, 2),
            atr=round(atr, 6),
            adx=round(adx, 2),
            comment="strong trend"
        )

    # normal trend
    if adx >= 20 and vol_norm > 0.0025:
        strength = min(10.0, 4 + (adx - 20) * 0.2)
        return MarketRegime(
            state="TREND",
            strength=round(strength, 2),
            atr=round(atr, 6),
            adx=round(adx, 2),
            comment="tradable trend"
        )

    # otherwise range
    strength = max(0.5, adx * 0.08)

    return MarketRegime(
        state="RANGE",
        strength=round(strength, 2),
        atr=round(atr, 6),
        adx=round(adx, 2),
        comment="range / chop"
    )
