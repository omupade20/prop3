# strategy/scanner.py

import json
import os
import threading
import time
from collections import deque, defaultdict
from datetime import datetime
from typing import Dict, List, Callable, Optional


DEFAULT_MAX_LEN = 300
ISOFMT = "%Y-%m-%dT%H:%M:%S"


def _now_iso():
    return datetime.now().strftime(ISOFMT)


class MarketScanner:

    def __init__(self, max_len: int = DEFAULT_MAX_LEN, snapshot_path: Optional[str] = None):

        self.max_len = max_len
        self.snapshot_path = snapshot_path

        self._bars: Dict[str, deque] = {}

        self._locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._global_lock = threading.Lock()

        self.last_alert_time: Dict[str, float] = {}
        self._dedupe_map: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._paused_until: Dict[str, float] = {}

        self._on_bar_close_callbacks: List[Callable[[str, dict], None]] = []

        self.bars_closed = 0
        self.replay_mode = False

        if self.snapshot_path:
            directory = os.path.dirname(self.snapshot_path)
            if directory:
                os.makedirs(directory, exist_ok=True)

    # ==========================================================
    # INTERNAL
    # ==========================================================

    def _ensure_inst(self, inst: str):

        with self._global_lock:
            if inst not in self._bars:
                self._bars[inst] = deque(maxlen=self.max_len)

    def _lock_for(self, inst: str):
        return self._locks[inst]

    # ==========================================================
    # INGESTION
    # ==========================================================

    def append_ohlc_bar(
        self,
        inst: str,
        time_iso: str,
        open_p: float,
        high_p: float,
        low_p: float,
        close_p: float,
        volume: float
    ) -> dict:

        self._ensure_inst(inst)

        bar = {
            "time": time_iso,
            "open": float(open_p),
            "high": float(high_p),
            "low": float(low_p),
            "close": float(close_p),
            "volume": float(volume)
        }

        with self._lock_for(inst):
            self._bars[inst].append(bar)
            self.bars_closed += 1

        for cb in list(self._on_bar_close_callbacks):
            try:
                cb(inst, bar)
            except Exception:
                pass

        return bar

    # ==========================================================
    # ACCESSORS
    # ==========================================================

    def get_last_n_bars(self, inst: str, n: int) -> List[dict]:

        if inst not in self._bars:
            return []

        with self._lock_for(inst):
            return list(self._bars[inst])[-n:]

    def get_highs(self, inst: str) -> List[float]:
        return [b["high"] for b in self.get_last_n_bars(inst, self.max_len)]

    def get_lows(self, inst: str) -> List[float]:
        return [b["low"] for b in self.get_last_n_bars(inst, self.max_len)]

    def get_closes(self, inst: str) -> List[float]:
        return [b["close"] for b in self.get_last_n_bars(inst, self.max_len)]

    def get_volumes(self, inst: str) -> List[float]:
        return [b["volume"] for b in self.get_last_n_bars(inst, self.max_len)]

    def has_enough_data(self, inst: str, min_bars: int = 30) -> bool:

        if inst not in self._bars:
            return False

        with self._lock_for(inst):
            return len(self._bars[inst]) >= min_bars

    def active_instruments(self) -> List[str]:
        return list(self._bars.keys())

    # ==========================================================
    # ALERT CONTROL
    # ==========================================================

    def can_emit_alert(self, inst: str, cooldown_seconds: int = 900) -> bool:

        now_ts = time.time()

        paused_until = self._paused_until.get(inst)

        if paused_until and now_ts < paused_until:
            return False

        last = self.last_alert_time.get(inst)

        if last is None:
            return True

        return (now_ts - last) >= cooldown_seconds

    def mark_alert_emitted(self, inst: str):
        self.last_alert_time[inst] = time.time()

    def dedupe_alert(self, inst: str, direction: str, window_seconds: int = 900) -> bool:

        now_ts = time.time()
        last = self._dedupe_map[inst].get(direction)

        if last and (now_ts - last) < window_seconds:
            return True

        self._dedupe_map[inst][direction] = now_ts
        return False

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def save_snapshot(self, path: Optional[str] = None):

        path = path or self.snapshot_path

        if not path:
            raise ValueError("No snapshot path configured")

        data = {
            "bars": {},
            "last_alert_time": self.last_alert_time,
            "dedupe_map": self._dedupe_map,
            "paused_until": self._paused_until,
            "timestamp": _now_iso()
        }

        with self._global_lock:
            for inst, dq in self._bars.items():
                data["bars"][inst] = list(dq)

        tmp = f"{path}.tmp"

        with open(tmp, "w") as f:
            json.dump(data, f)

        os.replace(tmp, path)
