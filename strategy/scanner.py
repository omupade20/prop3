# strategy/scanner.py

from collections import deque

class MarketScanner:
    """
    Enhanced scanner storing market data for multiple symbols.
    """

    def __init__(self, window_size=50, max_len=None):
        """
        window_size: fallback history length
        max_len: explicit history length if provided
        """
        self.max_len = max_len if max_len is not None else window_size

        # store recent values
        self.prices = {}
        self.highs = {}
        self.lows = {}
        self.closes = {}
        self.volumes = {}

    # internal helper
    def _init_store(self, store, inst):
        if inst not in store:
            store[inst] = deque(maxlen=self.max_len)

    def update(self, instrument, price, high, low, close, volume):
        """
        Update price & OHLC + volume for an instrument.
        Should be called on each new tick or bar.
        """
        # prices
        self._init_store(self.prices, instrument)
        self.prices[instrument].append(price)

        # high
        self._init_store(self.highs, instrument)
        self.highs[instrument].append(high)

        # low
        self._init_store(self.lows, instrument)
        self.lows[instrument].append(low)

        # close
        self._init_store(self.closes, instrument)
        self.closes[instrument].append(close)

        # volume
        self._init_store(self.volumes, instrument)
        self.volumes[instrument].append(volume)

    def get_prices(self, instrument):
        return list(self.prices.get(instrument, []))

    def get_highs(self, instrument):
        return list(self.highs.get(instrument, []))

    def get_lows(self, instrument):
        return list(self.lows.get(instrument, []))

    def get_closes(self, instrument):
        return list(self.closes.get(instrument, []))

    def get_volumes(self, instrument):
        return list(self.volumes.get(instrument, []))
