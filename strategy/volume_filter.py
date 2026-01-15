def volume_spike_confirmed(
    volume_history,
    threshold_multiplier: float = 1.25,  # Increased for stronger moves
    lookback: int = 20,
    rising_bars: int = 4  # More bars to confirm rising structure
):
    """
    Institutional-style volume confirmation.

    Confirms participation strength using:
    - Relative volume
    - Rising volume structure

    Returns:
        True if volume participation is valid
    """

    if not volume_history or len(volume_history) < lookback + rising_bars:
        return False

    recent = volume_history[-lookback:]
    avg_volume = sum(recent) / lookback
    current_volume = volume_history[-1]

    # --- Tier 1: Strong volume ---
    if current_volume >= avg_volume * 1.5:
        return True

    # --- Tier 2: Moderate volume ---
    if current_volume >= avg_volume * threshold_multiplier:
        return True

    # --- Tier 3: Rising volume (early participation) ---
    last_n = volume_history[-rising_bars:]
    if all(last_n[i] > last_n[i - 1] for i in range(1, len(last_n))):
        if current_volume >= avg_volume * 0.95:
            return True

    return False