# strategy/volume_filter.py

from dataclasses import dataclass
from typing import List


# =========================
# OUTPUT
# =========================

@dataclass
class VolumeContext:

    state: str
    score: float
    rel_volume: float
    avg_volume: float
    comment: str


# =========================
# VOLUME ANALYSIS
# =========================

def analyze_volume(
    volume_history: List[float],
    lookback: int = 20
) -> VolumeContext:

    """
    Participation quality for 5-minute candles.
    """

    if not volume_history or len(volume_history) < lookback:

        return VolumeContext(
            state="LOW",
            score=-0.4,
            rel_volume=0.0,
            avg_volume=0.0,
            comment="insufficient volume"
        )

    recent = volume_history[-lookback:]

    avg_vol = sum(recent) / lookback

    current = volume_history[-1]

    if avg_vol <= 0:

        return VolumeContext(
            state="LOW",
            score=-0.4,
            rel_volume=0.0,
            avg_volume=0.0,
            comment="zero volume"
        )

    rel = current / avg_vol

    # ======================
    # PARTICIPATION RULES
    # ======================

    if rel < 0.6:

        return VolumeContext(
            state="LOW",
            score=-0.5,
            rel_volume=round(rel, 2),
            avg_volume=round(avg_vol),
            comment="low participation"
        )

    if rel < 1.3:

        return VolumeContext(
            state="NORMAL",
            score=0.6,
            rel_volume=round(rel, 2),
            avg_volume=round(avg_vol),
            comment="normal participation"
        )

    return VolumeContext(
        state="HIGH",
        score=1.0,
        rel_volume=round(rel, 2),
        avg_volume=round(avg_vol),
        comment="high participation"
    )
