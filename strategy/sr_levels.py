# strategy/sr_levels.py

from typing import List, Dict, Optional, Tuple
from statistics import mean


# =========================
# SIMPLE SR FALLBACK
# =========================

def compute_simple_sr(highs: List[float], lows: List[float], lookback: int = 180):

    highs = highs[-lookback:] if highs else []
    lows = lows[-lookback:] if lows else []

    if not highs or not lows:
        return {"support": None, "resistance": None}

    return {
        "support": min(lows),
        "resistance": max(highs)
    }


# =========================
# LOCAL EXTREMA
# =========================

def _find_local_extrema(values: List[float], window: int = 5):

    n = len(values)

    maxima = []
    minima = []

    if n < window * 2 + 1:
        return maxima, minima

    half = window // 2

    for i in range(half, n - half):

        center = values[i]

        left = values[i - half:i]
        right = values[i + 1:i + 1 + half]

        if center > max(left) and center >= max(right):
            maxima.append((i, center))

        if center < min(left) and center <= min(right):
            minima.append((i, center))

    return maxima, minima


# =========================
# CLUSTER LEVELS
# =========================

def _cluster_levels(peaks: List[float], tol_pct: float = 0.006):

    if not peaks:
        return []

    sorted_peaks = sorted(peaks)

    clusters = []
    cluster = [sorted_peaks[0]]

    for p in sorted_peaks[1:]:

        avg = sum(cluster) / len(cluster)

        tol = avg * tol_pct

        if abs(p - avg) <= tol:
            cluster.append(p)
        else:
            clusters.append(cluster)
            cluster = [p]

    clusters.append(cluster)

    out = []

    for c in clusters:

        lvl = mean(c)

        out.append({
            "level": round(lvl, 6),
            "count": len(c),
            "strength": min(len(c), 5)
        })

    return out


# =========================
# MAIN SR CALCULATION
# =========================

def compute_sr_levels(
    highs: List[float],
    lows: List[float],
    lookback: int = 180,
    extrema_window: int = 5,
    cluster_tol_pct: float = 0.006,
    max_levels: int = 4
):

    highs_s = highs[-lookback:] if highs else []
    lows_s = lows[-lookback:] if lows else []

    if not highs_s or not lows_s:
        return {"supports": [], "resistances": []}

    max_extrema, _ = _find_local_extrema(highs_s, window=extrema_window)
    _, min_extrema = _find_local_extrema(lows_s, window=extrema_window)

    resistances = [val for _, val in max_extrema]
    supports = [val for _, val in min_extrema]

    resist_clusters = _cluster_levels(resistances, tol_pct=cluster_tol_pct)
    supp_clusters = _cluster_levels(supports, tol_pct=cluster_tol_pct)

    supp_sorted = sorted(supp_clusters, key=lambda x: x["level"], reverse=True)[:max_levels]
    res_sorted = sorted(resist_clusters, key=lambda x: x["level"], reverse=True)[:max_levels]

    return {
        "supports": supp_sorted,
        "resistances": res_sorted
    }


# =========================
# NEAREST SR
# =========================

def get_nearest_sr(
    price: float,
    sr_levels: Dict[str, List[Dict]],
    max_search_pct: float = 0.05
):

    if not sr_levels:
        return None

    supports = sr_levels.get("supports", [])
    resistances = sr_levels.get("resistances", [])

    best = None
    best_dist = float("inf")

    for s in supports:

        lvl = s["level"]

        dist = abs(price - lvl) / max(price, 1e-9)

        if dist < best_dist:
            best_dist = dist
            best = {
                "type": "support",
                "level": lvl,
                "dist_pct": dist,
                "strength": s.get("strength", 1)
            }

    for r in resistances:

        lvl = r["level"]

        dist = abs(price - lvl) / max(price, 1e-9)

        if dist < best_dist:
            best_dist = dist
            best = {
                "type": "resistance",
                "level": lvl,
                "dist_pct": dist,
                "strength": r.get("strength", 1)
            }

    if best and best["dist_pct"] <= max_search_pct:
        return best

    return None
