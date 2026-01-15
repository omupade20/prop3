# strategy/volatility_filter.py

def compute_true_range(highs, lows, closes):
    if len(highs) < 2:
        return []

    tr_values = []
    for i in range(1, len(highs)):
        tr_values.append(
            max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )
        )
    return tr_values


def compute_atr(highs, lows, closes, period=14):
    tr = compute_true_range(highs, lows, closes)
    if len(tr) < period:
        return None
    return sum(tr[-period:]) / period


def volatility_breakout_confirmed(
    current_move,
    atr_value,
    atr_multiplier=0.8,   # Increased for stronger directional moves
    min_move_pct=0.003   # Stricter fallback (avoids small noise)
):
    """
    Institutional-style volatility expansion check.

    - ATR-relative
    - Allows early breakout detection
    """

    if atr_value is None:
        return False

    # Absolute volatility expansion
    if abs(current_move) >= atr_value * atr_multiplier:
        return True

    # Fallback: % based expansion (protects low-ATR stocks)
    if atr_value > 0:
        move_pct = abs(current_move) / atr_value
        if move_pct >= min_move_pct:
            return True

    return False