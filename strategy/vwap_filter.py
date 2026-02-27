from collections import deque
from dataclasses import dataclass
from typing import Optional

# =========================
# VWAP Context Output
# =========================

@dataclass
class VWAPContext:
    vwap: Optional[float]
    distance_pct: float
    slope: float
    acceptance: str       # ABOVE | BELOW | NEAR
    pressure: str         # BUYING | SELLING | NEUTRAL
    score: float          # -2 .. +2
    comment: str


# =========================
# VWAP Calculator (5m)
# =========================

class VWAPCalculator:
    """
    Intraday VWAP for 5-minute system.

    Usage:
      - reset() at session start
      - update(close, volume) per 5m bar
      - get_context(price)
    """

    def __init__(self, window: Optional[int] = None, slope_window: int = 7):
        self.window = window
        self.slope_window = slope_window

        self.price_volume_sum = 0.0
        self.volume_sum = 0.0
        self.vwap_history = deque(maxlen=slope_window)

        if window:
            self.price_volume_deque = deque(maxlen=window)
            self.volume_deque = deque(maxlen=window)

        self.reset()

    # ---------------------
    # Session reset
    # ---------------------
    def reset(self):
        self.price_volume_sum = 0.0
        self.volume_sum = 0.0
        self.vwap_history.clear()

        if hasattr(self, "price_volume_deque"):
            self.price_volume_deque.clear()
            self.volume_deque.clear()

    # ---------------------
    # Update per 5m bar
    # ---------------------
    def update(self, price: float, volume: float) -> Optional[float]:
        if price is None or volume is None or volume <= 0:
            return None

        if self.window:
            self.price_volume_deque.append(price * volume)
            self.volume_deque.append(volume)
            self.price_volume_sum = sum(self.price_volume_deque)
            self.volume_sum = sum(self.volume_deque)
        else:
            self.price_volume_sum += price * volume
            self.volume_sum += volume

        if self.volume_sum <= 0:
            return None

        vwap = self.price_volume_sum / self.volume_sum
        self.vwap_history.append(vwap)
        return vwap

    # ---------------------
    # Access
    # ---------------------
    def get_vwap(self) -> Optional[float]:
        if self.volume_sum <= 0:
            return None
        return self.price_volume_sum / self.volume_sum

    # =========================
    # VWAP Context (5m)
    # =========================

    def get_context(self, price: float) -> VWAPContext:
        vwap = self.get_vwap()

        if vwap is None or price is None:
            return VWAPContext(
                vwap=None,
                distance_pct=0.0,
                slope=0.0,
                acceptance="NEAR",
                pressure="NEUTRAL",
                score=0.0,
                comment="VWAP unavailable"
            )

        # % distance
        distance_pct = (price - vwap) / vwap * 100.0

        # slope across recent 5m bars
        if len(self.vwap_history) >= 2:
            slope = (self.vwap_history[-1] - self.vwap_history[0]) / max(vwap, 1e-9)
        else:
            slope = 0.0

        # wider acceptance band for 5m
        if distance_pct > 0.3:
            acceptance = "ABOVE"
        elif distance_pct < -0.3:
            acceptance = "BELOW"
        else:
            acceptance = "NEAR"

        # pressure logic
        if acceptance == "ABOVE" and slope > 0:
            pressure = "BUYING"
            score = 1.5
            comment = "Above VWAP with rising slope"
        elif acceptance == "BELOW" and slope < 0:
            pressure = "SELLING"
            score = -1.5
            comment = "Below VWAP with falling slope"
        elif acceptance == "NEAR":
            pressure = "NEUTRAL"
            score = 0.0
            comment = "Near VWAP"
        else:
            pressure = "NEUTRAL"
            score = -0.4
            comment = "Weak VWAP alignment"

        score = max(min(score, 2.0), -2.0)

        return VWAPContext(
            vwap=round(vwap, 6),
            distance_pct=round(distance_pct, 3),
            slope=round(slope, 6),
            acceptance=acceptance,
            pressure=pressure,
            score=score,
            comment=comment
        )
