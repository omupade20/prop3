from strategy.market_regime import detect_market_regime
from strategy.htf_bias import get_htf_bias
from strategy.pullback_detector import detect_pullback_signal
from strategy.decision_engine import final_trade_decision
from strategy.vwap_filter import VWAPCalculator

class StrategyEngine:
"""
PURE 5-MINUTE SR PULLBACK ENGINE

```
Flow:
1m scanner → build 5m → regime → HTF → pullback → VWAP → decision
"""

def __init__(self, scanner, vwap_calculators, candle_builder_5m):
    self.scanner = scanner
    self.vwap_calculators = vwap_calculators
    self.candle_5m = candle_builder_5m

def evaluate(self, inst_key: str, ltp: float):

    # ==========================================
    # 1️⃣ GET LAST 1m BAR
    # ==========================================
    last_bar = self.scanner.get_last_n_bars(inst_key, 1)
    if not last_bar:
        return None

    bar = last_bar[0]

    # ==========================================
    # 2️⃣ BUILD / UPDATE 5m
    # ==========================================
    self.candle_5m.update(
        inst_key,
        bar["time"],
        bar["open"],
        bar["high"],
        bar["low"],
        bar["close"],
        bar["volume"]
    )

    hist_5m = self.candle_5m.get_history(inst_key, lookback=120)
    if not hist_5m or len(hist_5m) < 30:
        return None

    highs_5m = [c["high"] for c in hist_5m]
    lows_5m = [c["low"] for c in hist_5m]
    closes_5m = [c["close"] for c in hist_5m]
    volumes_5m = [c["volume"] for c in hist_5m]

    # ==========================================
    # 3️⃣ MARKET REGIME (5m)
    # ==========================================
    regime = detect_market_regime(
        highs=highs_5m,
        lows=lows_5m,
        closes=closes_5m
    )

    if regime.state == "RANGE":
        return None

    # ==========================================
    # 4️⃣ VWAP (5m aligned)
    # ==========================================
    if inst_key not in self.vwap_calculators:
        self.vwap_calculators[inst_key] = VWAPCalculator()

    vwap_calc = self.vwap_calculators[inst_key]

    last_5m_volume = volumes_5m[-1]
    last_5m_close = closes_5m[-1]

    vwap_calc.update(last_5m_close, last_5m_volume)
    vwap_ctx = vwap_calc.get_context(last_5m_close)

    # ==========================================
    # 5️⃣ HTF BIAS (5m)
    # ==========================================
    htf_bias = get_htf_bias(
        prices=closes_5m,
        vwap_value=vwap_ctx.vwap
    )

    # ==========================================
    # 6️⃣ PULLBACK DETECTION (5m)
    # ==========================================
    pullback = detect_pullback_signal(
        highs=highs_5m,
        lows=lows_5m,
        closes=closes_5m,
        volumes=volumes_5m,
        htf_direction=htf_bias.direction
    )

    if not pullback:
        return None

    # ==========================================
    # 7️⃣ FINAL DECISION
    # ==========================================
    decision = final_trade_decision(
        inst_key=inst_key,
        closes=closes_5m,
        volumes=volumes_5m,
        market_regime=regime.state,
        htf_bias_direction=htf_bias.direction,
        vwap_ctx=vwap_ctx,
        pullback_signal=pullback
    )

    # debug info
    decision.components["regime"] = regime.state
    decision.components["htf_bias"] = htf_bias.label

    return decision
```
