# ========================================
# File: CDXPOdata.py
# ========================================
import hmac
import hashlib
import json
import time
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("CD_API_KEY")
API_SECRET = os.getenv("CD_API_SECRET")

print("💡 CDXPOdata.py loaded from:", __file__)  # Confirms correct file is used

def get_xrp_data():
    """
    Fetch positions and current XRP-USDT price.
    Returns a dictionary for safe key-based access.
    """
    key = API_KEY
    secret = API_SECRET
    secret_bytes = bytes(secret, encoding="utf-8")

    timestamp = int(round(time.time() * 1000))

    body = {
        "timestamp": timestamp,
        "page": "1",
        "size": "10",
        "pairs": "B-XRP_USDT",
        "margin_currency_short_name": ["INR"]
    }

    json_body = json.dumps(body, separators=(",", ":"))
    signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()

    url = "https://api.coindcx.com/exchange/v1/derivatives/futures/positions"
    headers = {
        "Content-Type": "application/json",
        "X-AUTH-APIKEY": key,
        "X-AUTH-SIGNATURE": signature
    }

    # Default values
    data_dict = {
        "active_pos": 0.0,
        "inactive_buy": 0.0,
        "inactive_sell": 0.0,
        "avg_price": 0.0,
        "take_profit": 0.0,
        "stop_loss": 0.0,
        "locked_order_margin": 0.0,
        "XRPCurentPrice": 0.0
    }

    # Fetch positions
    try:
        response = requests.post(url, data=json_body, headers=headers, timeout=10)
        positions = response.json()
        if positions:
            item = positions[0]
            data_dict["active_pos"] = float(item.get("active_pos", 0.0))
            data_dict["inactive_buy"] = float(item.get("inactive_pos_buy", 0.0))
            data_dict["inactive_sell"] = float(item.get("inactive_pos_sell", 0.0))
            data_dict["avg_price"] = float(item.get("avg_price", 0.0))
            data_dict["take_profit"] = float(item.get("take_profit_trigger", 0.0))
            data_dict["stop_loss"] = float(item.get("stop_loss_trigger", 0.0))
            data_dict["locked_order_margin"] = float(item.get("locked_order_margin", 0.0))
    except Exception as e:
        print("⚠️ Error fetching positions:", e)

    # Fetch current price
    try:
        url_price = "https://api.coindcx.com/exchange/ticker"
        resp = requests.get(url_price, timeout=10).json()
        for t in resp:
            if t["market"] in ["XRPUSDT", "B-XRP_USDT", "XRP-USDT"]:
                data_dict["XRPCurentPrice"] = float(t.get("last_price") or t.get("lastPrice") or 0.0)
                break
    except Exception as e:
        print("⚠️ Error fetching price:", e)

    # Fallback if price is 0
    if data_dict["XRPCurentPrice"] <= 0:
        if data_dict["avg_price"] > 0:
            data_dict["XRPCurentPrice"] = data_dict["avg_price"]
        elif data_dict["stop_loss"] > 0:
            data_dict["XRPCurentPrice"] = data_dict["stop_loss"]

    return data_dict