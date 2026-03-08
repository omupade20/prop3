# strategy/strategy_engine.py

from strategy.market_regime import detect_market_regime
from strategy.htf_bias import get_htf_bias
from strategy.pullback_detector import detect_pullback_signal
from strategy.decision_engine import final_trade_decision


class StrategyEngine:

    """
    Simplified 5-Minute SR Pullback Engine
    """

    def __init__(self, scanner):

        self.scanner = scanner


    def evaluate(self, inst_key: str, ltp: float):

        # ======================================
        # 1️⃣ DATA SUFFICIENCY
        # ======================================

        if not self.scanner.has_enough_data(inst_key, min_bars=30):
            return None

        highs = self.scanner.get_highs(inst_key)
        lows = self.scanner.get_lows(inst_key)
        closes = self.scanner.get_closes(inst_key)
        volumes = self.scanner.get_volumes(inst_key)

        if not highs or not lows or not closes or not volumes:
            return None


        # ======================================
        # 2️⃣ MARKET REGIME
        # ======================================

        regime = detect_market_regime(
            highs=highs,
            lows=lows,
            closes=closes
        )

        # Ignore chop markets
        if regime.state == "RANGE":
            return None


        # ======================================
        # 3️⃣ HTF BIAS
        # ======================================

        htf_bias = get_htf_bias(
            prices=closes
        )


        # ======================================
        # 4️⃣ PULLBACK DETECTION
        # ======================================

        pullback = detect_pullback_signal(
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            htf_direction=htf_bias.direction
        )

        if not pullback:
            return None


        # ======================================
        # 5️⃣ FINAL DECISION
        # ======================================

        decision = final_trade_decision(
            inst_key=inst_key,
            closes=closes,
            volumes=volumes,
            market_regime=regime.state,
            htf_bias_direction=htf_bias.direction,
            pullback_signal=pullback
        )

        if not decision:
            return None


        # ======================================
        # 6️⃣ ATTACH CONTEXT
        # ======================================

        decision.components["regime"] = regime.state
        decision.components["htf_bias"] = htf_bias.label

        return decision
