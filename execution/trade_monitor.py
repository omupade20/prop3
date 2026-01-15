# execution/trade_monitor.py

from datetime import datetime
from execution.execution_config import (
    STOP_LOSS_PCT,
    TARGET_PCT,
    BREAKEVEN_MOVE_PCT,
    PARTIAL_EXIT_MOVE_PCT,
    PARTIAL_EXIT_LIMIT_PCT
)

class TrackedTrade:
    """
    Holds state for a live trade.
    """

    def __init__(self, inst_key, side, entry_price, qty):
        self.inst_key = inst_key
        self.side = side          # "BUY" or "SELL"
        self.entry_price = entry_price
        self.qty = qty

        self.stop_loss = self.calc_stop_loss(entry_price, side)
        self.target = self.calc_target(entry_price, side)
        self.breakeven_moved = False
        self.partial_exit_done = False
        self.is_closed = False

        self.open_time = datetime.now()

    def calc_stop_loss(self, entry_price, side):
        if side == "BUY":
            return entry_price * (1 - STOP_LOSS_PCT)
        else:
            return entry_price * (1 + STOP_LOSS_PCT)

    def calc_target(self, entry_price, side):
        if side == "BUY":
            return entry_price * (1 + TARGET_PCT)
        else:
            return entry_price * (1 - TARGET_PCT)

    def get_current_profit_pct(self, current_price):
        if self.side == "BUY":
            return (current_price - self.entry_price) / self.entry_price
        return (self.entry_price - current_price) / self.entry_price


class TradeMonitor:
    """
    Monitors live trades and triggers exit logic.
    """

    def __init__(self):
        self.active_trades = {}

    def add_trade(self, trade_id, inst_key, side, entry_price, qty):
        self.active_trades[trade_id] = TrackedTrade(
            inst_key, side, entry_price, qty
        )

    def remove_trade(self, trade_id):
        if trade_id in self.active_trades:
            del self.active_trades[trade_id]

    def check_trades(self, current_prices):
        """
        Check each active trade against exit conditions.

        current_prices: dict { inst_key: current_price }
        """

        exits = []

        for trade_id, trade in list(self.active_trades.items()):
            if trade.is_closed:
                continue

            ltp = current_prices.get(trade.inst_key)
            if ltp is None:
                continue

            profit_pct = trade.get_current_profit_pct(ltp)

            # 1) STOP LOSS
            if trade.side == "BUY" and ltp <= trade.stop_loss:
                exits.append((trade_id, "STOP_LOSS", ltp))
                trade.is_closed = True
                continue
            if trade.side == "SELL" and ltp >= trade.stop_loss:
                exits.append((trade_id, "STOP_LOSS", ltp))
                trade.is_closed = True
                continue

            # 2) TARGET
            if trade.side == "BUY" and ltp >= trade.target:
                exits.append((trade_id, "TARGET", ltp))
                trade.is_closed = True
                continue
            if trade.side == "SELL" and ltp <= trade.target:
                exits.append((trade_id, "TARGET", ltp))
                trade.is_closed = True
                continue

            # 3) BREAKEVEN STEP
            if not trade.breakeven_moved:
                if profit_pct >= BREAKEVEN_MOVE_PCT:
                    trade.stop_loss = trade.entry_price
                    trade.breakeven_moved = True

            # 4) PARTIAL EXIT (0.7 move then fail back)
            if not trade.partial_exit_done:
                if profit_pct >= PARTIAL_EXIT_MOVE_PCT:
                    # reached the zone for partial exit
                    # now check if retraces below threshold
                    if trade.side == "BUY" and ltp <= trade.entry_price * (1 + PARTIAL_EXIT_LIMIT_PCT):
                        exits.append((trade_id, "PARTIAL_EXIT", ltp))
                        trade.is_closed = True
                        continue
                    if trade.side == "SELL" and ltp >= trade.entry_price * (1 - PARTIAL_EXIT_LIMIT_PCT):
                        exits.append((trade_id, "PARTIAL_EXIT", ltp))
                        trade.is_closed = True
                        continue

        return exits
