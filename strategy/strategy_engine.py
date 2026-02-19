from strategy.market_regime import detect_market_regime
from strategy.htf_bias import get_htf_bias
from strategy.pullback_detector import detect_pullback_signal
from strategy.decision_engine import final_trade_decision

from strategy.vwap_filter import VWAPCalculator
from strategy.mtf_builder import MTFBuilder
from strategy.mtf_context import analyze_mtf


class StrategyEngine:
    """
    CONTINUATION PULLBACK STRATEGY ENGINE

    Hierarchy:
    MTF → Regime → HTF → VWAP → 5m SR Pullback → Decision
    """

    def __init__(self, scanner, vwap_calculators):
        self.scanner = scanner
        self.vwap_calculators = vwap_calculators
        self.mtf_builder = MTFBuilder()

    def evaluate(self, inst_key: str, ltp: float):

        # ==================================================
        # 1️⃣ DATA SUFFICIENCY
        # ==================================================

        if not self.scanner.has_enough_data(inst_key, min_bars=50):
            return None

        prices_1m = self.scanner.get_prices(inst_key)
        highs_1m = self.scanner.get_highs(inst_key)
        lows_1m = self.scanner.get_lows(inst_key)
        closes_1m = self.scanner.get_closes(inst_key)
        volumes_1m = self.scanner.get_volumes(inst_key)

        if not (prices_1m and highs_1m and lows_1m and closes_1m and volumes_1m):
            return None

        # ==================================================
        # 2️⃣ UPDATE MTF BUILDER
        # ==================================================

        last_bar = self.scanner.get_last_n_bars(inst_key, 1)
        if not last_bar:
            return None

        bar = last_bar[0]

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
        hist_5m = self.mtf_builder.get_tf_history(inst_key, minutes=5, lookback=40)

        candle_15m = self.mtf_builder.get_latest_15m(inst_key)
        hist_15m = self.mtf_builder.get_tf_history(inst_key, minutes=15, lookback=3)

        if not candle_5m or len(hist_5m) < 20:
            return None

        # Extract 5m highs/lows
        highs_5m = [c["high"] for c in hist_5m]
        lows_5m = [c["low"] for c in hist_5m]

        # ==================================================
        # 3️⃣ MTF CONTEXT
        # ==================================================

        mtf_ctx = analyze_mtf(
            candle_5m,
            candle_15m,
            history_5m=hist_5m,
            history_15m=hist_15m
        )

        if mtf_ctx.direction == "NEUTRAL":
            return None

        if mtf_ctx.conflict:
            return None

        # ==================================================
        # 4️⃣ MARKET REGIME
        # ==================================================

        regime = detect_market_regime(
            highs=highs_1m,
            lows=lows_1m,
            closes=closes_1m
        )

        if regime.state in ("WEAK", "COMPRESSION"):
            return None

        # ==================================================
        # 5️⃣ VWAP CONTEXT
        # ==================================================

        if inst_key not in self.vwap_calculators:
            self.vwap_calculators[inst_key] = VWAPCalculator()

        vwap_calc = self.vwap_calculators[inst_key]

        vwap_calc.update(
            ltp,
            volumes_1m[-1]
        )

        vwap_ctx = vwap_calc.get_context(ltp)

        # ==================================================
        # 6️⃣ HTF BIAS
        # ==================================================

        htf_bias = get_htf_bias(
            prices=prices_1m,
            vwap_value=vwap_ctx.vwap
        )

        if mtf_ctx.direction == "BULLISH" and htf_bias.direction != "BULLISH":
            return None

        if mtf_ctx.direction == "BEARISH" and htf_bias.direction != "BEARISH":
            return None

        # ==================================================
        # 7️⃣ CONTINUATION PULLBACK DETECTOR (5m SR)
        # ==================================================

        pullback = detect_pullback_signal(
            prices_1m=prices_1m,
            highs_1m=highs_1m,
            lows_1m=lows_1m,
            closes_1m=closes_1m,
            volumes_1m=volumes_1m,
            highs_5m=highs_5m,
            lows_5m=lows_5m,
            htf_direction=mtf_ctx.direction
        )

        if not pullback:
            return None

        # ==================================================
        # 8️⃣ FINAL DECISION
        # ==================================================

        decision = final_trade_decision(
            inst_key=inst_key,
            prices=prices_1m,
            highs=highs_1m,
            lows=lows_1m,
            closes=closes_1m,
            volumes=volumes_1m,
            market_regime=regime.state,
            htf_bias_direction=htf_bias.direction,
            vwap_ctx=vwap_ctx,
            pullback_signal=pullback
        )

        # Debug context
        decision.components["mtf_direction"] = mtf_ctx.direction
        decision.components["mtf_strength"] = mtf_ctx.strength
        decision.components["regime"] = regime.state
        decision.components["htf_bias"] = htf_bias.label

        return decision
