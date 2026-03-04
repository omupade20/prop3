import json
import datetime
from collections import defaultdict

import upstox_client
from config.settings import ACCESS_TOKEN

from strategy.scanner import MarketScanner
from strategy.vwap_filter import VWAPCalculator
from strategy.strategy_engine import StrategyEngine

from execution.execution_engine import ExecutionEngine
from execution.order_executor import OrderExecutor
from execution.trade_monitor import TradeMonitor
from execution.risk_manager import RiskManager
from execution.trade_logger import TradeLogger


FEED_MODE = "full"

# ---------------- LOAD UNIVERSE ----------------
with open("data/nifty500_keys.json", "r") as f:
    INSTRUMENT_LIST = json.load(f)


# ---------------- CORE OBJECTS ----------------
scanner = MarketScanner(max_len=600)

vwap_calculators = {
    inst: VWAPCalculator() for inst in INSTRUMENT_LIST
}

strategy_engine = StrategyEngine(
    scanner,
    vwap_calculators
)

order_executor = OrderExecutor()
trade_monitor = TradeMonitor()
risk_manager = RiskManager()
trade_logger = TradeLogger()

execution_engine = ExecutionEngine(
    order_executor,
    trade_monitor,
    risk_manager,
    trade_logger
)


signals_today = {}
last_bar_time = {}
ALLOW_NEW_TRADES = True


# ===============================
# 5-MINUTE AGGREGATION BUFFER
# ===============================

five_min_builder = defaultdict(list)


# ===============================
# STREAMER
# ===============================

def start_market_streamer():

    global ALLOW_NEW_TRADES

    config = upstox_client.Configuration()
    config.access_token = ACCESS_TOKEN
    api_client = upstox_client.ApiClient(config)

    streamer = upstox_client.MarketDataStreamerV3(
        api_client,
        INSTRUMENT_LIST,
        FEED_MODE
    )


    def on_message(message):

        global ALLOW_NEW_TRADES

        feeds = message.get("feeds", {})
        now = datetime.datetime.now()
        today = now.date().isoformat()

        if today not in signals_today:
            signals_today[today] = set()

        current_prices = {}


        for inst_key, feed_info in feeds.items():

            data = feed_info.get("fullFeed", {}).get("marketFF", {})

            # ---------------- LTP ----------------
            try:
                ltp = float(data["ltpc"]["ltp"])
            except Exception:
                continue

            current_prices[inst_key] = ltp


            # ---------------- OHLC DATA ----------------
            ohlc = data.get("marketOHLC", {}).get("ohlc", [])

            if not ohlc:
                continue

            bar = ohlc[-1]

            try:
                high = float(bar["high"])
                low = float(bar["low"])
                close = float(bar["close"])
                volume = float(bar["vol"])
                ts = bar["ts"]
            except Exception:
                continue


            # prevent duplicate minute bars
            prev_ts = last_bar_time.get(inst_key)

            if prev_ts == ts:
                continue

            last_bar_time[inst_key] = ts


            dt = datetime.datetime.fromtimestamp(ts / 1000)

            # ===============================
            # BUILD 5 MINUTE BAR
            # ===============================

            five_min_builder[inst_key].append({

                "open": close,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "ts": ts

            })


            # wait until 5 bars collected
            if len(five_min_builder[inst_key]) < 5:
                continue


            bars = five_min_builder[inst_key]

            five_min_builder[inst_key] = []


            open_p = bars[0]["open"]

            close_p = bars[-1]["close"]

            high_p = max(b["high"] for b in bars)

            low_p = min(b["low"] for b in bars)

            vol = sum(b["volume"] for b in bars)


            bar_time = datetime.datetime.fromtimestamp(
                bars[-1]["ts"] / 1000
            )

            bar_iso = bar_time.replace(
                second=0,
                microsecond=0
            ).isoformat()


            # ===============================
            # APPEND 5m BAR TO SCANNER
            # ===============================

            scanner.append_ohlc_bar(

                inst_key,
                bar_iso,
                open_p,
                high_p,
                low_p,
                close_p,
                vol

            )


            # ===============================
            # STRATEGY EVALUATION
            # ===============================

            decision = strategy_engine.evaluate(
                inst_key,
                ltp
            )

            if not decision:
                continue


            if decision.state.startswith("EXECUTE"):

                if inst_key in signals_today[today]:
                    continue


                signals_today[today].add(inst_key)


                execution_engine.handle_entry(

                    inst_key,
                    decision,
                    ltp

                )


        # ===============================
        # EXIT MANAGEMENT
        # ===============================

        execution_engine.handle_exits(

            current_prices,
            now

        )


    streamer.on("message", on_message)

    streamer.connect()

    print("🚀 5-Minute Pullback Trading System LIVE")
