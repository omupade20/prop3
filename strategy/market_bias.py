# strategy/market_bias.py

def get_market_bias(
    nifty_price: float,
    nifty_vwap: float,
    ema20: float,
    ema50: float
):
    """
    Decide overall market mood using NIFTY 50.

    Returns:
        "BULLISH", "BEARISH", or "SIDEWAYS"
    """

    # Safety check
    if None in (nifty_price, nifty_vwap, ema20, ema50):
        return "SIDEWAYS"

    # Bullish condition
    if nifty_price > nifty_vwap and ema20 > ema50:
        return "BULLISH"

    # Bearish condition
    if nifty_price < nifty_vwap and ema20 < ema50:
        return "BEARISH"

    # Otherwise market is not clear
    return "SIDEWAYS"
