"""
MarketScanner (5-minute native, production-ready).

Responsibilities:
- Store rolling 5-minute OHLCV bars per instrument
- Provide fast OHLCV access for strategy
- Trigger callbacks on new 5m bar close
- Handle alert throttling / dedupe
- Snapshot save/load
- Thread-safe for websocket ingestion
"""

import json
import os
import threading
import time
from collections import deque, defaultdict
from datetime import datetime
from typing import Dict, List, Callable, Optional

# ~3 trading days of 5m bars (≈ 75 bars/day)
DEFAULT_MAX_LEN = 300

ISOFMT = "%Y-%m-%dT%H:%M:%S"


def _now_iso():
    return datetime.now().strftime(ISOFMT)


class MarketScanner:
    def __init__(
        self,
        max_len: int = DEFAULT_MAX_LEN,
        snapshot_path: Optional[str] = None
    ):
        self.max_len = max_len
        self.snapshot_path = snapshot_path

        # per-instrument deque of 5m bars
        # bar = {time, open, high, low, close, volume}
        self._bars: Dict[str, deque] = {}
        self._locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._global_lock = threading.Lock()

        # alert state
        self.last_alert_time: Dict[str, float] = {}
        self._dedupe_map: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._paused_until: Dict[str, float] = {}

        # callbacks when 5m bar closes
        self._on_bar_close_callbacks: List[Callable[[str, dict], None]] = []

        # metrics
        self.bars_closed = 0
        self.replay_mode = False

        if self.snapshot_path:
            os.makedirs(os.path.dirname(self.snapshot_path), exist_ok=True)

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
    # INGESTION (5m CLOSED BAR)
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
        """
        Ingest a completed 5-minute bar.
        Safe from websocket thread.
        """
        self._ensure_inst(inst)

        bar = {
            "time": time_iso,
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "volume": volume
        }

        with self._lock_for(inst):
            self._bars[inst].append(bar)
            self.bars_closed += 1

        # trigger callbacks outside lock
        for cb in list(self._on_bar_close_callbacks):
            try:
                cb(inst, bar)
            except Exception:
                pass

        return bar

    # backward compatibility wrapper
    def update(
        self,
        instrument: str,
        price: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        time_iso: Optional[str] = None
    ):
        if time_iso:
            self.append_ohlc_bar(
                instrument,
                time_iso,
                price,
                high,
                low,
                close,
                volume
            )

    # ==========================================================
    # ACCESSORS
    # ==========================================================

    def get_last_n_bars(self, inst: str, n: int) -> List[dict]:
        if inst not in self._bars:
            return []
        with self._lock_for(inst):
            return list(self._bars[inst])[-n:]

    def get_last_bar(self, inst: str) -> Optional[dict]:
        if inst not in self._bars or not self._bars[inst]:
            return None
        with self._lock_for(inst):
            return dict(self._bars[inst][-1])

    def get_prices(self, inst: str) -> List[float]:
        return [b["close"] for b in self.get_last_n_bars(inst, self.max_len)]

    def get_highs(self, inst: str) -> List[float]:
        return [b["high"] for b in self.get_last_n_bars(inst, self.max_len)]

    def get_lows(self, inst: str) -> List[float]:
        return [b["low"] for b in self.get_last_n_bars(inst, self.max_len)]

    def get_closes(self, inst: str) -> List[float]:
        return [b["close"] for b in self.get_last_n_bars(inst, self.max_len)]

    def get_volumes(self, inst: str) -> List[float]:
        return [b["volume"] for b in self.get_last_n_bars(inst, self.max_len)]

    def has_enough_data(self, inst: str, min_bars: int = 30) -> bool:
        return inst in self._bars and len(self._bars[inst]) >= min_bars

    def active_instruments(self) -> List[str]:
        return list(self._bars.keys())

    # ==========================================================
    # CALLBACKS
    # ==========================================================

    def register_on_bar_close(self, cb: Callable[[str, dict], None]):
        if cb not in self._on_bar_close_callbacks:
            self._on_bar_close_callbacks.append(cb)

    def unregister_on_bar_close(self, cb: Callable[[str, dict], None]):
        if cb in self._on_bar_close_callbacks:
            self._on_bar_close_callbacks.remove(cb)

    # ==========================================================
    # ALERT THROTTLING
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

    def dedupe_alert(
        self,
        inst: str,
        direction: str,
        window_seconds: int = 900
    ) -> bool:
        now_ts = time.time()
        last = self._dedupe_map[inst].get(direction)

        if last and (now_ts - last) < window_seconds:
            return True

        self._dedupe_map[inst][direction] = now_ts
        return False

    def mark_instrument_paused(self, inst: str, until_ts: float):
        self._paused_until[inst] = until_ts

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

    def load_snapshot(self, path: Optional[str] = None) -> bool:
        path = path or self.snapshot_path
        if not path or not os.path.exists(path):
            return False

        with open(path, "r") as f:
            data = json.load(f)

        with self._global_lock:
            for inst, bars in data.get("bars", {}).items():
                self._bars[inst] = deque(bars, maxlen=self.max_len)

            self.last_alert_time = data.get("last_alert_time", {})
            self._dedupe_map = defaultdict(dict, data.get("dedupe_map", {}))
            self._paused_until = data.get("paused_until", {})

        return True

    # ==========================================================
    # REPLAY (BACKTEST / SIM)
    # ==========================================================

    def replay_bars(
        self,
        inst: str,
        bars: List[dict],
        call_callbacks: bool = False
    ):
        self.replay_mode = True
        self._ensure_inst(inst)

        with self._lock_for(inst):
            for bar in bars:
                if not all(k in bar for k in ("time", "open", "high", "low", "close", "volume")):
                    continue

                self._bars[inst].append(bar)
                self.bars_closed += 1

                if call_callbacks:
                    for cb in list(self._on_bar_close_callbacks):
                        try:
                            cb(inst, bar)
                        except Exception:
                            pass

        self.replay_mode = False
