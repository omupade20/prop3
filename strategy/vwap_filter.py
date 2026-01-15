# strategy/vwap_filter.py

from collections import deque

class VWAPCalculator:
    """
    Calculates intraday VWAP (Volume Weighted Average Price) for a stock.
    RSI: Must reset at the start of each day/trading session.
    """

    def __init__(self, window=None):
        """
        window: optional max number of samples to hold — not strictly needed,
        but allows limiting memory use. If None, full session data is stored.
        """
        self.price_volume_sum = 0.0
        self.volume_sum = 0.0
        self.reset()

        self.window = window
        if window:
            self.price_volume_deque = deque(maxlen=window)
            self.volume_deque = deque(maxlen=window)

    def reset(self):
        """
        Reset for a new trading session.
        """
        self.price_volume_sum = 0.0
        self.volume_sum = 0.0

        if hasattr(self, "price_volume_deque"):
            self.price_volume_deque.clear()
            self.volume_deque.clear()

    def update(self, price, volume):
        """
        Update VWAP calculation for a new tick/bar.

        price: last traded price or typical price for a bar
        volume: volume of that bar
        """
        if volume is None or price is None:
            return None

        # Add to rolling deques if window configured
        if self.window:
            self.price_volume_deque.append(price * volume)
            self.volume_deque.append(volume)

            self.price_volume_sum = sum(self.price_volume_deque)
            self.volume_sum = sum(self.volume_deque)
        else:
            # Full session accumulation
            self.price_volume_sum += price * volume
            self.volume_sum += volume

        if self.volume_sum == 0:
            return None

        return self.price_volume_sum / self.volume_sum

    def get_vwap(self):
        """
        Returns the current VWAP.
        """
        if self.volume_sum == 0:
            return None
        return self.price_volume_sum / self.volume_sum
