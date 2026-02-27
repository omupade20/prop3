from strategy.market_regime import detect_market_regime
from strategy.htf_bias import get_htf_bias
from strategy.pullback_detector import detect_pullback_signal
from strategy.decision_engine import final_trade_decision

from strategy.vwap_filter import VWAPCalculator
from strategy.mtf_builder import MTFBuilder
from strategy.mtf_context import analyze_mtf


class StrategyEngine:
    """
    5-Minute SR Pullback Strategy Engine

    Architecture:
    1m scanner → 5m/15m MTF → regime/HTF → VWAP → pullback → decision
    """

    def __init__(self, scanner, vwap_calculators):
        self.scanner = scanner
        self.vwap_calculators = vwap_calculators
        self.mtf_builder = MTFBuilder()

    def evaluate(self, inst_key: str, ltp: float):

        # ==========================================
        # 1️⃣ REQUIRE BASE DATA
        # ==========================================
        if not self.scanner.has_enough_data(inst_key, min_bars=50):
            return None

        last_bar = self.scanner.get_last_n_bars(inst_key, 1)
        if not last_bar:
            return None

        bar = last_bar[0]

        # ==========================================
        # 2️⃣ BUILD MTF (5m / 15m)
        # ==========================================
        self.mtf_builder.update(
            inst_key,
            bar["time"],
            bar["open"],
            bar["high"],
            bar["low"],
            bar["close"],
            bar["volume"]
        )

        candle_5m = self.mtf_builder.get_latest_5m(inst_key)
        candle_15m = self.mtf_builder.get_latest_15m(inst_key)

        hist_5m = self.mtf_builder.get_tf_history(inst_key, minutes=5, lookback=60)
        hist_15m = self.mtf_builder.get_tf_history(inst_key, minutes=15, lookback=40)

        if not hist_5m or len(hist_5m) < 20:
            return None

        # ==========================================
        # 3️⃣ MTF DIRECTION CONTEXT
        # ==========================================
        mtf_ctx = analyze_mtf(
            candle_5m,
            candle_15m,
            history_5m=hist_5m,
            history_15m=hist_15m
        )

        if mtf_ctx.direction == "NEUTRAL" or mtf_ctx.conflict:
            return None

        # ==========================================
        # 4️⃣ 5-MIN REGIME (NOT 1m)
        # ==========================================
        highs_5m = [c["high"] for c in hist_5m]
        lows_5m = [c["low"] for c in hist_5m]
        closes_5m = [c["close"] for c in hist_5m]
        volumes_5m = [c["volume"] for c in hist_5m]

        regime = detect_market_regime(
            highs=highs_5m,
            lows=lows_5m,
            closes=closes_5m
        )

        if regime.state in ("WEAK", "COMPRESSION"):
            return None

        # ==========================================
        # 5️⃣ VWAP (1m stream)
        # ==========================================
        if inst_key not in self.vwap_calculators:
            self.vwap_calculators[inst_key] = VWAPCalculator()

        vwap_calc = self.vwap_calculators[inst_key]
        vwap_calc.update(ltp, bar["volume"])

        vwap_ctx = vwap_calc.get_context(ltp)

        # ==========================================
        # 6️⃣ HTF BIAS (5m STRUCTURE)
        # ==========================================
        htf_bias = get_htf_bias(
            prices=closes_5m,
            vwap_value=vwap_ctx.vwap
        )

        if mtf_ctx.direction == "BULLISH" and htf_bias.direction != "BULLISH":
            return None

        if mtf_ctx.direction == "BEARISH" and htf_bias.direction != "BEARISH":
            return None

        # ==========================================
        # 7️⃣ PULLBACK (5m)
        # ==========================================
        pullback = detect_pullback_signal(
            prices=closes_5m,
            highs=highs_5m,
            lows=lows_5m,
            closes=closes_5m,
            volumes=volumes_5m,
            htf_direction=mtf_ctx.direction
        )

        if not pullback:
            return None

        # ==========================================
        # 8️⃣ DECISION
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

        # debug context
        decision.components["mtf_direction"] = mtf_ctx.direction
        decision.components["mtf_strength"] = mtf_ctx.strength
        decision.components["regime"] = regime.state
        decision.components["htf_bias"] = htf_bias.label

        return decision
