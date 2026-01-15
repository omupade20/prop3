# execution/trade_logger.py

import csv
import os
import datetime


class TradeLogger:
    """
    Logs all completed trades into ONE master CSV file.
    """

    def __init__(self, file_path="logs/trades/all_trades.csv"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        self._ensure_header()

    def _ensure_header(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, mode="w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "date",
                    "entry_time",
                    "exit_time",
                    "instrument",
                    "side",
                    "quantity",
                    "entry_price",
                    "exit_price",
                    "pnl_pct",
                    "pnl_amount",
                    "exit_reason",
                    "strategy",
                    "remarks"
                ])

    def log_trade(
        self,
        instrument: str,
        side: str,
        quantity: int,
        entry_price: float,
        exit_price: float,
        entry_time: datetime.datetime,
        exit_time: datetime.datetime,
        exit_reason: str,
        strategy: str = "elite_intraday_v1",
        remarks: str = ""
    ):
        """
        Append one completed trade to the master CSV.
        """

        pnl_pct = (
            ((exit_price - entry_price) / entry_price) * 100
            if side == "BUY"
            else ((entry_price - exit_price) / entry_price) * 100
        )

        pnl_amount = (
            (exit_price - entry_price) * quantity
            if side == "BUY"
            else (entry_price - exit_price) * quantity
        )

        with open(self.file_path, mode="a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                entry_time.date().isoformat(),
                entry_time.strftime("%H:%M:%S"),
                exit_time.strftime("%H:%M:%S"),
                instrument,
                side,
                quantity,
                round(entry_price, 2),
                round(exit_price, 2),
                round(pnl_pct, 2),
                round(pnl_amount, 2),
                exit_reason,
                strategy,
                remarks
            ])
