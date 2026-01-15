# execution/order_executor.py

import math
import upstox_client
from upstox_client.rest import ApiException
from config.settings import ACCESS_TOKEN
from execution.execution_config import (
    CAPITAL_PER_TRADE,
    LIMIT_BUFFER_PCT
)

class OrderExecutor:
    """
    Places limit orders using Upstox API.
    """

    def __init__(self):
        # Setup API client
        config = upstox_client.Configuration()
        config.access_token = ACCESS_TOKEN
        self.api_client = upstox_client.ApiClient(config)

        # Order API (V3 recommended)
        self.order_api = upstox_client.OrderApiV3(self.api_client)

    def calculate_quantity(self, price: float) -> int:
        """
        Calculate number of shares based on configured capital.
        Only whole shares are allowed.
        """
        if price <= 0:
            return 0

        qty = math.floor(CAPITAL_PER_TRADE / price)
        return qty

    def place_limit_order(
        self,
        inst_key: str,
        side: str,
        price: float
    ) -> dict | None:
        """
        Places a LIMIT order on Upstox using current LTP + buffer.
        """

        # Determine quantity based on capital
        qty = self.calculate_quantity(price)
        if qty < 1:
            print(f"[OrderExecutor] Not enough capital for 1 share at ₹{price:.2f}. Skipped.")
            return None

        # Adjust limit price with buffer
        if side == "BUY":
            limit_price = price * (1 + LIMIT_BUFFER_PCT)
            txn_type = "BUY"
        elif side == "SELL":
            limit_price = price * (1 - LIMIT_BUFFER_PCT)
            txn_type = "SELL"
        else:
            print(f"[OrderExecutor] Unknown side: {side}")
            return None

        # Build request model
        body = upstox_client.PlaceOrderV3Request(
            quantity=qty,
            product="I",                # Intraday (MIS)
            validity="DAY",
            price=round(limit_price, 2),
            instrument_token=inst_key,
            order_type="LIMIT",
            transaction_type=txn_type,
            disclosed_quantity=0,
            trigger_price=0.0,
            is_amo=False
        )

        # Try placing the order
        try:
            response = self.order_api.place_order(body)
            print(f"[OrderExecutor] Placed {side} LIMIT {qty} @ {round(limit_price,2)} for {inst_key}")
            return response.to_dict()
        except ApiException as e:
            print(f"[OrderExecutor] API error placing order for {inst_key}: {e}")
            return None
        except Exception as e:
            print(f"[OrderExecutor] Unexpected error: {e}")
            return None
