# strategy/breakout_detector.py

from typing import Optional
from strategy.volume_filter import volume_spike_confirmed
from strategy.volatility_filter import compute_atr


def detect_compression(prices, lookback=20, compression_ratio=0.65):
    """
    Detect controlled volatility contraction before expansion.
    """
    if len(prices) < lookback * 2:
        return False

    recent = prices[-lookback:]
    previous = prices[-lookback * 2:-lookback]

    recent_range = max(recent) - min(recent)
    previous_range = max(previous) - min(previous)

    if previous_range == 0:
        return False

    return recent_range < previous_range * compression_ratio


def breakout_signal_confirmed(
    inst_key: str,
    prices: list[float],
    volume_history: Optional[list[float]] = None,
    high_prices: Optional[list[float]] = None,
    low_prices: Optional[list[float]] = None,
    close_prices: Optional[list[float]] = None,
    breakout_pct: float = 0.0020,  # Increased for cleaner institutional breakouts
    vol_threshold: float = 1.15,
    atr_multiplier: float = 0.7
):
    """
    EARLY breakout detection (institutional-style).
    Returns: "LONG", "SHORT", or None
    """

    if len(prices) < 30:
        return None

    # --- 1️⃣ Compression (MANDATORY) ---
    if not detect_compression(prices):
        return None

    # --- 2️⃣ ATR-based expansion (PRIMARY) ---
    atr_ok = False
    recent_move = abs(prices[-1] - prices[-2])

    if high_prices and low_prices and close_prices:
        atr = compute_atr(high_prices, low_prices, close_prices, period=14)
        if atr and recent_move >= atr * atr_multiplier:
            atr_ok = True

    # --- 3️⃣ Volume confirmation (SECONDARY) ---
    volume_ok = False
    if volume_history and len(volume_history) >= 20:
        volume_ok = volume_spike_confirmed(
            volume_history,
            threshold_multiplier=vol_threshold
        )

    # Require at least ONE confirmation
    if not (atr_ok or volume_ok):
        return None

    # --- 4️⃣ Directional breakout ---
    recent_segment = prices[-20:]
    high = max(recent_segment[:-1])
    low = min(recent_segment[:-1])
    current = recent_segment[-1]

    if current > high * (1 + breakout_pct):
        return "LONG"

    if current < low * (1 - breakout_pct):
        return "SHORT"

    return None