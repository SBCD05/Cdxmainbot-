# coindcx_tpsl.py
import hmac
import hashlib
import json
import time
import requests
import os
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

API_KEY = os.getenv("CD_API_KEY")
API_SECRET = os.getenv("CD_API_SECRET")

secret_bytes = bytes(API_SECRET, encoding='utf-8')

def set_tpsl(position_id, tp_price, sl_price):
    """
    Place Take Profit and Stop Loss on a position.
    
    :param position_id: str - Position ID
    :param tp_price: str - Take profit trigger price
    :param sl_price: str - Stop loss trigger price
    :return: dict - API response
    """
    timeStamp = int(round(time.time() * 1000))

    body = {
        "timestamp": timeStamp,
        "id": position_id,
        "take_profit": {
            "stop_price": tp_price,
            "order_type": "take_profit_market"
        },
        "stop_loss": {
            "stop_price": sl_price,
            "order_type": "stop_market"
        }
    }

    json_body = json.dumps(body, separators=(',', ':'))
    signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()

    url = "https://api.coindcx.com/exchange/v1/derivatives/futures/positions/create_tpsl"

    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': API_KEY,
        'X-AUTH-SIGNATURE': signature
    }

    response = requests.post(url, data=json_body, headers=headers)
    return response.json()