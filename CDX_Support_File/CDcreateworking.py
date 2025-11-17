# order_module.py
import hmac
import hashlib
import json
import time
import requests
import os
from dotenv import load_dotenv

# Load API keys from .env
load_dotenv()
API_KEY = os.getenv("CD_API_KEY")
API_SECRET = os.getenv("CD_API_SECRET")
secret_bytes = bytes(API_SECRET, encoding="utf-8")

# URL for creating futures orders
URL = "https://api.coindcx.com/exchange/v1/derivatives/futures/orders/create"

def place_orders(orders):
    """
    Place multiple orders on CoinDCX Futures.
    
    orders: list of dicts, each dict must include:
        side, pair, price, quantity, sl, tp, leverage, order_type
    """
    results = []

    for order in orders:
        timestamp = int(round(time.time() * 1000))

        body = {
            "timestamp": timestamp,
            "order": {
                "margin_currency_short_name": "INR",
                "position_margin_type": "isolated",
                "side": order["side"],                   # buy/sell
                "pair": order["pair"],                   # e.g., B-XRP_USDT
                "order_type": order.get("order_type", "limit_order"),  # default: limit_order
                "price": order.get("price", 0),          # only needed for limit orders
                "total_quantity": order["quantity"],
                "leverage": order["leverage"],
                "notification": "email_notification",
                "time_in_force": "good_till_cancel",
                "hidden": False,
                "post_only": False,
                "take_profit_price": order.get("tp"),
                "stop_loss_price": order.get("sl"),
            },
        }

        json_body = json.dumps(body, separators=(",", ":"))
        signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-AUTH-APIKEY": API_KEY,
            "X-AUTH-SIGNATURE": signature,
        }

        response = requests.post(URL, data=json_body, headers=headers)
        try:
            data = response.json()
        except Exception:
            data = response.text

        results.append({"pair": order["pair"], "response": data})

    return results