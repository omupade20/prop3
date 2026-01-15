# strategy/indicators.py

from collections import deque

def simple_moving_average(prices, period):
    """
    Compute Simple Moving Average (SMA) for the given period.
    prices: a list of recent prices
    period: length for SMA
    """
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def exponential_moving_average(prices, period):
    """
    Compute Exponential Moving Average (EMA).
    Uses formula that applies weighting factor.
    """
    if len(prices) < period:
        return None

    # start by computing simple average for the first EMA
    sma = simple_moving_average(prices[:period], period)
    multiplier = 2 / (period + 1)

    ema_previous = sma
    for price in prices[period:]:
        ema_previous = (price - ema_previous) * multiplier + ema_previous
    return ema_previous


def relative_strength_index(prices, period=14):
    """
    Compute RSI using a list of prices.
    RSI = 100 - (100 / (1 + RS))
    RS = average_gain / average_loss
    """
    if len(prices) < period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, period + 1):
        delta = prices[-i] - prices[-i - 1]
        if delta > 0:
            gains.append(delta)
        else:
            losses.append(abs(delta))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
