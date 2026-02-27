from collections import defaultdict
from datetime import datetime
from typing import Optional, Dict


class Candle5mBuilder:
    """
    Aggregates 1-minute bars into 5-minute candles.

    update(...) returns True ONLY when a 5m candle closes.
    Strategy should evaluate only on True.
    """

    def __init__(self):
        self._buffers: Dict[str, Dict] = defaultdict(dict)
        self._last_5m_time: Dict[str, str] = {}

    def _floor_5m(self, iso_time: str) -> str:
        dt = datetime.fromisoformat(iso_time)
        minute = (dt.minute // 5) * 5
        floored = dt.replace(minute=minute, second=0, microsecond=0)
        return floored.isoformat()

    def update(
        self,
        inst: str,
        time_iso: str,
        open_p: float,
        high_p: float,
        low_p: float,
        close_p: float,
        volume: float
    ) -> bool:
        """
        Feed closed 1-minute bar.

        Returns:
            True  → a 5-minute candle just closed
            False → still building
        """

        bucket = self._floor_5m(time_iso)
        buf = self._buffers.get(inst)

        # start new 5m buffer
        if not buf or buf["time"] != bucket:
            # previous bucket exists → that 5m just closed
            if buf:
                self._last_5m_time[inst] = buf["time"]

            # start new buffer
            self._buffers[inst] = {
                "time": bucket,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": volume,
            }

            # return True only when previous existed
            return buf is not None

        # update current 5m
        buf["high"] = max(buf["high"], high_p)
        buf["low"] = min(buf["low"], low_p)
        buf["close"] = close_p
        buf["volume"] += volume

        return False

    # =========================
    # Accessors
    # =========================

    def get_latest(self, inst: str) -> Optional[Dict]:
        return self._buffers.get(inst)

    def get_last_closed_time(self, inst: str) -> Optional[str]:
        return self._last_5m_time.get(inst)
