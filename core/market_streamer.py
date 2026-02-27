from strategy.market_regime import detect_market_regime
from strategy.htf_bias import get_htf_bias
from strategy.pullback_detector import detect_pullback_signal
from strategy.decision_engine import final_trade_decision
from strategy.vwap_filter import VWAPCalculator


class StrategyEngine:
    """
    PURE 5-MINUTE SR PULLBACK ENGINE

    Uses:
    - scanner 5m bars
    - SR pullback detection
    - VWAP environment
    - HTF bias
    """

    def __init__(self, scanner, vwap_calculators):
        self.scanner = scanner
        self.vwap_calculators = vwap_calculators

    def evaluate(self, inst_key: str, ltp: float):

        # =========================
        # 1️⃣ DATA
        # =========================
        if not self.scanner.has_enough_data(inst_key, min_bars=50):
            return None

        highs = self.scanner.get_highs(inst_key)
        lows = self.scanner.get_lows(inst_key)
        closes = self.scanner.get_closes(inst_key)
        volumes = self.scanner.get_volumes(inst_key)

        if not closes or len(closes) < 30:
            return None

        # =========================
        # 2️⃣ MARKET REGIME (5m)
        # =========================
        regime = detect_market_regime(
            highs=highs,
            lows=lows,
            closes=closes
        )

        if regime.state == "RANGE":
            return None

        # =========================
        # 3️⃣ VWAP
        # =========================
        if inst_key not in self.vwap_calculators:
            self.vwap_calculators[inst_key] = VWAPCalculator()

        vwap_calc = self.vwap_calculators[inst_key]
        vwap_calc.update(ltp, volumes[-1] if volumes else 0)
        vwap_ctx = vwap_calc.get_context(ltp)

        # =========================
        # 4️⃣ HTF BIAS
        # =========================
        htf_bias = get_htf_bias(
            prices=closes,
            vwap_value=vwap_ctx.vwap
        )

        # =========================
        # 5️⃣ PULLBACK
        # =========================
        pullback = detect_pullback_signal(
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            htf_direction=htf_bias.direction
        )

        if not pullback:
            return None

        # =========================
        # 6️⃣ DECISION
        # =========================
        decision = final_trade_decision(
            inst_key=inst_key,
            closes=closes,
            volumes=volumes,
            market_regime=regime.state,
            htf_bias_direction=htf_bias.direction,
            vwap_ctx=vwap_ctx,
            pullback_signal=pullback
        )

        # debug info
        decision.components["regime"] = regime.state
        decision.components["htf_bias"] = htf_bias.label

        return decision
