# strategy/liquidity_filter.py

def is_liquid(volume_history, min_avg_volume=250000):
    """
    Determines if a stock has sufficient liquidity.

    volume_history: list of recent volume values
    min_avg_volume: minimum average volume threshold

    Returns:
        True if average volume over recent bars >= min_avg_volume
    """

    if not volume_history:
        return False

    # Compute average over recent volume history
    avg_vol = sum(volume_history) / len(volume_history)

    # Check if average volume meets threshold
    if avg_vol >= min_avg_volume:
        return True

    return False