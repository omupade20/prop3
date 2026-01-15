# core/market_streamer.py

import json
import datetime
import upstox_client
from config.settings import ACCESS_TOKEN
from execution.trade_logger import TradeLogger

# Scanner + Strategy Modules
from strategy.scanner import MarketScanner
from strategy.market_regime import detect_market_regime
from strategy.htf_bias import get_htf_bias
from strategy.breakout_detector import breakout_signal_confirmed
from strategy.vwap_filter import VWAPCalculator
from strategy.decision_engine import final_trade_decision

# Execution modules
from execution.order_executor import OrderExecutor
from execution.trade_monitor import TradeMonitor
from execution.risk_manager import RiskManager

# ---------------- CONFIG ----------------

FEED_MODE = "full"

# Load instrument list for NIFTY500
with open("data/nifty500_keys.json", "r") as f:
    INSTRUMENT_LIST = json.load(f)

scanner = MarketScanner(max_len=600)
vwap_calculators = {inst: VWAPCalculator() for inst in INSTRUMENT_LIST}

# Execution helpers
order_executor = OrderExecutor()
trade_monitor = TradeMonitor()
risk_manager = RiskManager()

# Trade CSV Logger (completed trades only)
trade_logger = TradeLogger()

signals_today = {}

# Allow new trades until risk manager stops
ALLOW_NEW_TRADES = True


# ---------------- STREAMER ----------------

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

        if not ALLOW_NEW_TRADES:
            return

        feeds = message.get("feeds", {})
        now = datetime.datetime.now()
        today = now.date().isoformat()

        if today not in signals_today:
            signals_today[today] = set()

        # Build a map of current prices for monitoring
        current_prices = {}

        for inst_key, feed_info in feeds.items():
            data = feed_info.get("fullFeed", {}).get("marketFF", {})

            # --- Last traded price (LTP) ---
            try:
                ltp = float(data["ltpc"]["ltp"])
            except Exception:
                continue

            current_prices[inst_key] = ltp

            # --- 1-min OHLC + Volume ---
            ohlc = data.get("marketOHLC", {}).get("ohlc", [])
            if not ohlc:
                continue

            bar = ohlc[-1]
            try:
                high = float(bar.get("high"))
                low = float(bar.get("low"))
                close = float(bar.get("close"))
                volume = float(bar.get("vol"))
            except Exception:
                continue

            # --- Update scanner ---
            scanner.update(inst_key, ltp, high, low, close, volume)

            prices_1m = scanner.get_prices(inst_key)
            if len(prices_1m) < 30:
                continue

            highs = scanner.get_highs(inst_key)
            lows = scanner.get_lows(inst_key)
            closes = scanner.get_closes(inst_key)
            volumes = scanner.get_volumes(inst_key)

            # --- Market Regime ---
            market_regime = detect_market_regime(highs, lows, closes)

            # --- VWAP ---
            vwap_val = vwap_calculators[inst_key].update(ltp, volume)

            # --- HTF Bias ---
            htf_bias = get_htf_bias(prices_1m, vwap_value=vwap_val)

            # --- Breakout detection ---
            breakout_signal = breakout_signal_confirmed(
                inst_key=inst_key,
                prices=prices_1m,
                volume_history=volumes,
                high_prices=highs,
                low_prices=lows,
                close_prices=closes
            )

            if breakout_signal is None:
                continue

            # --- Final decision ---
            decision = final_trade_decision(
                inst_key=inst_key,
                prices=prices_1m,
                market_regime=market_regime,
                htf_bias=htf_bias,
                breakout_signal=breakout_signal,
                vwap_val=vwap_val,
                ltp=ltp
            )

            if decision in ("BUY", "SELL"):
                if inst_key in signals_today[today]:
                    continue

                signals_today[today].add(inst_key)

                # Risk check
                if not risk_manager.can_trade_now():
                    ALLOW_NEW_TRADES = False
                    continue

                # Place entry order
                order_result = order_executor.place_limit_order(
                    inst_key=inst_key,
                    side=decision,
                    price=ltp
                )

                if order_result:
                    order_id = order_result.get("order_id") or order_result.get("orderId")
                    qty = order_result.get("quantity", 0)

                    trade_monitor.add_trade(
                        trade_id=order_id,
                        inst_key=inst_key,
                        side=decision,
                        entry_price=ltp,
                        qty=qty
                    )

        # ---------------- EXIT HANDLING ----------------

        exits = trade_monitor.check_trades(current_prices)

        for trade_id, reason, exit_price in exits:
            trade = trade_monitor.trades.get(trade_id)
            if not trade:
                continue

            # Log completed trade to CSV
            trade_logger.log_trade(
                instrument=trade.inst_key,
                side=trade.side,
                quantity=trade.qty,
                entry_price=trade.entry_price,
                exit_price=exit_price,
                entry_time=trade.entry_time,
                exit_time=now,
                exit_reason=reason,
                strategy="elite_intraday_v1"
            )

            # Record for risk manager
            risk_manager.record_trade_outcome(reason)

            trade_monitor.remove_trade(trade_id)

            if not risk_manager.can_trade_now():
                ALLOW_NEW_TRADES = False

    streamer.on("message", on_message)
    streamer.connect()

    print("🚀 Trading system started — Live execution enabled.")
