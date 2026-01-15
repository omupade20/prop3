# strategy/decision_engine.py

from strategy.indicators import exponential_moving_average, relative_strength_index


def final_trade_decision(
    inst_key: str,
    prices: list[float],
    market_regime: str,
    htf_bias: str,
    breakout_signal: str,
    vwap_val: float,
    ltp: float
):
    """
    Institutional-grade final decision engine.

    Returns:
        "BUY", "SELL", or None
    """

    # --- 1️⃣ Market regime gate ---
    if market_regime not in ("TRENDING", "EARLY_TREND"):
        return None

    # --- 2️⃣ Breakout must exist ---
    if breakout_signal not in ("LONG", "SHORT"):
        return None

    # --- 3️⃣ HTF bias alignment (soft) ---
    if breakout_signal == "LONG":
        if htf_bias not in ("BULLISH_STRONG", "BULLISH_WEAK"):
            return None

    if breakout_signal == "SHORT":
        if htf_bias not in ("BEARISH_STRONG", "BEARISH_WEAK"):
            return None

    # --- 4️⃣ VWAP context (NOT a hard gate) ---
    vwap_ok = True
    if vwap_val:
        if breakout_signal == "LONG" and ltp < vwap_val * 0.997:
            vwap_ok = False
        if breakout_signal == "SHORT" and ltp > vwap_val * 1.003:
            vwap_ok = False

    # Allow weak VWAP violation only if HTF is strong
    if not vwap_ok:
        if breakout_signal == "LONG" and htf_bias != "BULLISH_STRONG":
            return None
        if breakout_signal == "SHORT" and htf_bias != "BEARISH_STRONG":
            return None

    # --- 5️⃣ Momentum confirmation ---
    if len(prices) < 30:
        return None

    ema9 = exponential_moving_average(prices, 9)
    ema21 = exponential_moving_average(prices, 21)
    rsi14 = relative_strength_index(prices, 14)

    if ema9 is None or ema21 is None or rsi14 is None:
        return None

    # --- 6️⃣ Entry logic ---
    if breakout_signal == "LONG":
        if ema9 > ema21 and rsi14 > 48:
            return "BUY"

    if breakout_signal == "SHORT":
        if ema9 < ema21 and rsi14 < 52:
            return "SELL"

    return None
