# strategy/vwap_filter.py

from collections import deque
from dataclasses import dataclass
from typing import Optional


# =========================
# OUTPUT
# =========================

@dataclass
class VWAPContext:

    vwap: Optional[float]
    distance_pct: float
    slope: float
    acceptance: str
    pressure: str
    score: float
    comment: str


# =========================
# VWAP CALCULATOR
# =========================

class VWAPCalculator:

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


    # ======================
    # RESET
    # ======================

    def reset(self):

        self.price_volume_sum = 0.0
        self.volume_sum = 0.0

        self.vwap_history.clear()

        if hasattr(self, "price_volume_deque"):

            self.price_volume_deque.clear()
            self.volume_deque.clear()


    # ======================
    # UPDATE
    # ======================

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


    # ======================
    # GET VWAP
    # ======================

    def get_vwap(self) -> Optional[float]:

        if self.volume_sum <= 0:
            return None

        return self.price_volume_sum / self.volume_sum


    # ======================
    # VWAP CONTEXT
    # ======================

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

        # distance %
        distance_pct = (price - vwap) / vwap * 100

        # slope
        if len(self.vwap_history) >= 2:

            slope = self.vwap_history[-1] - self.vwap_history[0]

        else:

            slope = 0.0

        # acceptance zone (wider)
        if distance_pct > 0.5:

            acceptance = "ABOVE"

        elif distance_pct < -0.5:

            acceptance = "BELOW"

        else:

            acceptance = "NEAR"


        # pressure logic

        if acceptance == "ABOVE" and slope > 0:

            pressure = "BUYING"
            score = 1.2
            comment = "above rising VWAP"

        elif acceptance == "BELOW" and slope < 0:

            pressure = "SELLING"
            score = -1.2
            comment = "below falling VWAP"

        elif acceptance == "NEAR":

            pressure = "NEUTRAL"
            score = 0.0
            comment = "near VWAP"

        else:

            pressure = "NEUTRAL"
            score = -0.2
            comment = "weak VWAP alignment"


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
