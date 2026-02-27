from strategy.market_regime import detect_market_regime
from strategy.htf_bias import get_htf_bias
from strategy.pullback_detector import detect_pullback_signal
from strategy.decision_engine import final_trade_decision
from strategy.vwap_filter import VWAPCalculator


class StrategyEngine:
    """
    PURE 5-MINUTE SR PULLBACK ENGINE

    Flow:
    1m scanner → build 5m → regime/HTF → pullback → VWAP → decision
    """

    def __init__(self, scanner, vwap_calculators, candle_builder_5m):
        self.scanner = scanner
        self.vwap_calculators = vwap_calculators
        self.candle_5m = candle_builder_5m  # simple 5m builder

    def evaluate(self, inst_key: str, ltp: float):

        # ==========================================
        # 1️⃣ BASE DATA
        # ==========================================
        if not self.scanner.has_enough_data(inst_key, min_bars=50):
            return None

        last_bar = self.scanner.get_last_n_bars(inst_key, 1)
        if not last_bar:
            return None

        bar = last_bar[0]

        # ==========================================
        # 2️⃣ BUILD 5-MIN CANDLE
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
        # 3️⃣ REGIME (5m)
        # ==========================================
        regime = detect_market_regime(
            highs=highs_5m,
            lows=lows_5m,
            closes=closes_5m
        )

        if regime.state in ("WEAK", "COMPRESSION"):
            return None

        # ==========================================
        # 4️⃣ VWAP (1m stream)
        # ==========================================
        if inst_key not in self.vwap_calculators:
            self.vwap_calculators[inst_key] = VWAPCalculator()

        vwap_calc = self.vwap_calculators[inst_key]
        vwap_calc.update(ltp, bar["volume"])
        vwap_ctx = vwap_calc.get_context(ltp)

        # ==========================================
        # 5️⃣ HTF BIAS (5m)
        # ==========================================
        htf_bias = get_htf_bias(
            prices=closes_5m,
            vwap_value=vwap_ctx.vwap
        )

        # ==========================================
        # 6️⃣ PULLBACK (5m)
        # ==========================================
        pullback = detect_pullback_signal(
            prices=closes_5m,
            highs=highs_5m,
            lows=lows_5m,
            closes=closes_5m,
            volumes=volumes_5m,
            htf_direction=htf_bias.direction
        )

        if not pullback:
            return None

        # ==========================================
        # 7️⃣ DECISION
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
