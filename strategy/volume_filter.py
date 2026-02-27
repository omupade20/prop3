from dataclasses import dataclass
from typing import List


@dataclass
class VolumeContext:
    state: str      # LOW | NORMAL | HIGH
    score: float    # -1 .. +1.5
    rel_volume: float
    avg_volume: float
    comment: str


def analyze_volume(
    volume_history: List[float],
    lookback: int = 20
) -> VolumeContext:
    """
    5-minute participation quality.

    LOW     → weak participation
    NORMAL  → tradable
    HIGH    → strong participation
    """

    if not volume_history or len(volume_history) < lookback:
        return VolumeContext("LOW", -0.5, 0.0, 0.0, "insufficient volume")

    recent = volume_history[-lookback:]
    avg_vol = sum(recent) / lookback
    current = volume_history[-1]

    if avg_vol <= 0:
        return VolumeContext("LOW", -0.5, 0.0, 0.0, "zero volume")

    rel = current / avg_vol

    # thresholds tuned for 5m equities
    if rel < 0.7:
        return VolumeContext(
            state="LOW",
            score=-0.6,
            rel_volume=round(rel, 2),
            avg_volume=round(avg_vol),
            comment="low participation"
        )

    if rel < 1.4:
        return VolumeContext(
            state="NORMAL",
            score=0.6,
            rel_volume=round(rel, 2),
            avg_volume=round(avg_vol),
            comment="normal participation"
        )

    return VolumeContext(
        state="HIGH",
        score=1.2,
        rel_volume=round(rel, 2),
        avg_volume=round(avg_vol),
        comment="high participation"
    )
