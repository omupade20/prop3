# strategy/advanced_indicators.py

from collections import deque
import math

def compute_macd(prices, short_period=12, long_period=26, signal_period=9):
    """
    Compute MACD, Signal, and Histogram.
    MACD line = EMA(short_period) - EMA(long_period)
    Signal line = EMA of MACD line
    """
    if len(prices) < long_period:
        return None

    # Helper for EMA
    def ema(series, period):
        k = 2 / (period + 1)
        ema_val = series[0]
        for price in series[1:]:
            ema_val = (price - ema_val) * k + ema_val
        return ema_val

    short_ema = ema(prices, short_period)
    long_ema = ema(prices, long_period)

    macd_line = short_ema - long_ema

    # Build macd history (simple approximation using last values)
    macd_hist = [short_ema - long_ema]
    for i in range(1, min(len(prices), signal_period)):
        macd_hist.append(macd_hist[-1])

    signal_line = ema(macd_hist, signal_period)
    histogram = macd_line - signal_line

    return {"macd": macd_line, "signal": signal_line, "hist": histogram}


def compute_true_range(highs, lows, closes):
    """
    True Range = max(
      current high - current low,
      abs(current high - previous close),
      abs(current low - previous close)
    )
    """
    if len(highs) < 2:
        return None
    tr = []
    for i in range(1, len(highs)):
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        ))
    return tr


def compute_atr(highs, lows, closes, period=14):
    """
    Average True Range: measure of volatility.
    """
    trs = compute_true_range(highs, lows, closes)
    if not trs or len(trs) < period:
        return None
    return sum(trs[-period:]) / period


def compute_adx(highs, lows, closes, period=14):
    """
    Approximate ADX (Average Directional Index)
    """
    if len(highs) < period + 1:
        return None

    # Calculate directional moves
    plus_dm, minus_dm = [], []
    for i in range(1, len(highs)):
        up_move = highs[i] - highs[i-1]
        down_move = lows[i-1] - lows[i]
        plus_dm.append(max(up_move, 0) if up_move > down_move else 0)
        minus_dm.append(max(down_move, 0) if down_move > up_move else 0)

    atr_val = compute_atr(highs, lows, closes, period)
    if atr_val is None:
        return None

    plus_di = (sum(plus_dm[-period:]) / atr_val) * 100
    minus_di = (sum(minus_dm[-period:]) / atr_val) * 100

    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) != 0 else 0

    # Smooth ADX over period
    adx_val = sum([dx] * period) / period
    return adx_val
