# strategy/market_regime.py

from typing import List

# -----------------------------
# Core Calculations
# -----------------------------

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


def compute_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14):
    tr = compute_true_range(highs, lows, closes)
    if len(tr) < period:
        return None
    return sum(tr[-period:]) / period


def compute_adx(highs: List[float], lows: List[float], closes: List[float], period: int = 14):
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
        return 0

    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100
    return dx  # lightweight ADX for intraday
        

# -----------------------------
# Market Regime Logic
# -----------------------------

def detect_market_regime(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    adx_trend: float = 23,   # Increased for stronger trends
    adx_early: float = 18    # Stricter early trend detection
) -> str:
    """
    Returns:
        TRENDING       -> strong trend
        EARLY_TREND    -> start of expansion (ideal for entries)
        SIDEWAYS       -> no trade
    """

    adx = compute_adx(highs, lows, closes)
    atr = compute_atr(highs, lows, closes)

    if adx is None or atr is None:
        return "SIDEWAYS"

    # --- Strong trend ---
    if adx >= adx_trend:
        return "TRENDING"

    # --- Early expansion detection ---
    recent_range = max(highs[-10:]) - min(lows[-10:])
    previous_range = max(highs[-20:-10]) - min(lows[-20:-10])

    if adx >= adx_early and recent_range > previous_range * 1.6:
        return "EARLY_TREND"

    return "SIDEWAYS"