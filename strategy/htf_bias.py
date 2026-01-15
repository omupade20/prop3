# strategy/htf_bias.py

from strategy.indicators import exponential_moving_average


def get_htf_bias(
    prices,
    vwap_value=None,
    short_period=20,
    long_period=50,
    vwap_tolerance=0.006  # Increased for stronger trend commitment
):
    """
    Institutional-style HTF bias.

    Returns:
        BULLISH_STRONG
        BULLISH_WEAK
        BEARISH_STRONG
        BEARISH_WEAK
        NEUTRAL
    """

    if len(prices) < long_period:
        return "NEUTRAL"

    ema_short = exponential_moving_average(prices, short_period)
    ema_long = exponential_moving_average(prices, long_period)

    if ema_short is None or ema_long is None:
        return "NEUTRAL"

    price = prices[-1]

    # EMA-based bias
    if ema_short > ema_long:
        ema_bias = "BULLISH"
    elif ema_short < ema_long:
        ema_bias = "BEARISH"
    else:
        return "NEUTRAL"

    # VWAP alignment (soft)
    vwap_bias = None
    if vwap_value:
        if price > vwap_value * (1 + vwap_tolerance):
            vwap_bias = "BULLISH"
        elif price < vwap_value * (1 - vwap_tolerance):
            vwap_bias = "BEARISH"

    # Combine EMA + VWAP
    if ema_bias == "BULLISH":
        if vwap_bias == "BULLISH":
            return "BULLISH_STRONG"
        return "BULLISH_WEAK"

    if ema_bias == "BEARISH":
        if vwap_bias == "BEARISH":
            return "BEARISH_STRONG"
        return "BEARISH_WEAK"

    return "NEUTRAL"