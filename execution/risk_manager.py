# execution/risk_manager.py

from execution.execution_config import (
    MAX_STOP_LOSSES,
    MAX_TARGET_HITS,
    MAX_PARTIAL_EXITS,
    MAX_TRADES_PER_DAY
)

class RiskManager:
    """
    Keeps track of closed trades and enforces daily risk limits.
    """

    def __init__(self):
        self.reset_daily_counters()

    def reset_daily_counters(self):
        self.stop_losses = 0
        self.target_hits = 0
        self.partial_exits = 0
        self.total_trades = 0

    def record_trade_outcome(self, exit_reason: str):
        """
        Called when a trade closes.
        exit_reason should be one of:
            "STOP_LOSS", "TARGET", "PARTIAL_EXIT"
        """
        self.total_trades += 1

        if exit_reason == "STOP_LOSS":
            self.stop_losses += 1

        elif exit_reason == "TARGET":
            self.target_hits += 1

        elif exit_reason == "PARTIAL_EXIT":
            self.partial_exits += 1

    def can_trade_now(self) -> bool:
        """
        Returns True if trading should still continue today
        based on risk limits, otherwise False.
        """
        # Stop if daily max trades reached
        if self.total_trades >= MAX_TRADES_PER_DAY:
            return False

        # Stop if stop-losses limit reached
        if self.stop_losses >= MAX_STOP_LOSSES:
            return False

        # Stop if full targets limit reached
        if self.target_hits >= MAX_TARGET_HITS:
            return False

        # Stop if too many partial exits
        if self.partial_exits >= MAX_PARTIAL_EXITS:
            return False

        return True

    def get_current_status(self) -> dict:
        """
        Return a snapshot of current risk counters.
        Useful for logging and reporting.
        """
        return {
            "total_trades": self.total_trades,
            "stop_losses": self.stop_losses,
            "target_hits": self.target_hits,
            "partial_exits": self.partial_exits,
            "can_trade": self.can_trade_now(),
        }
