# ============================================================
# FILE: xrp_Bye_Sell_atr_signal.py  (ONE-SHOT Combo-3 Engine)
# WebSocket runs until a VALID BUY/SELL + ATR condition met.
# ============================================================

import requests
import pandas as pd
import pandas_ta as ta
import json
from websocket import WebSocketApp
from datetime import datetime

# ---------- Binance API ----------
BINANCE_REST = "http://api.binance.com/api/v3/klines"
BINANCE_WS   = "wss://stream.binance.com:9443/ws/xrpusdt@kline_5m"

# ---------- Strategy Inputs ----------
MACD_FAST = 2
MACD_SLOW = 20
MACD_SIGNAL = 3

EMA_FAST = 20
EMA_SLOW = 50

ATR_PERIOD = 14
MIN_ATR = 0.005          # IGNORE CANDLES IF ATR BELOW THIS

# ============================================================
# ONE-SHOT LIVE SIGNAL ENGINE
# ============================================================

class DataEngine:
    def __init__(self):
        self.df = pd.DataFrame()
        self.ws = None

        self.final_signal = None
        self.final_price = None
        self.final_atr = None

        self.done = False

    # --------------------------------------------------------
    def load_historical(self, limit=500):

        params = {
            "symbol": "XRPUSDT",
            "interval": "5m",
            "limit": limit
        }

        r = requests.get(BINANCE_REST, params=params)
        df = pd.DataFrame(r.json())

        df.columns = [
            "open_time","open","high","low","close","volume",
            "close_time","qav","num","tbb","tbq","ignore"
        ]

        df["datetime"] = pd.to_datetime(df["open_time"], unit="ms")
        df.set_index("datetime", inplace=True)
        df = df[["open","high","low","close","volume"]].astype(float)

        # --- indicators ---
        df.ta.macd(fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL, append=True)
        df[f"ema{EMA_FAST}"] = df["close"].ewm(span=EMA_FAST, adjust=False).mean()
        df[f"ema{EMA_SLOW}"] = df["close"].ewm(span=EMA_SLOW, adjust=False).mean()

        df["ATR"] = ta.atr(df["high"], df["low"], df["close"], length=ATR_PERIOD)
        df["MAX_ATR"] = df["ATR"].rolling(ATR_PERIOD).max()

        self.df = df

    # --------------------------------------------------------
    # WEBSOCKET HANDLER
    # --------------------------------------------------------
    def on_message(self, ws, message):

        if self.done:
            return

        data = json.loads(message)
        k = data["k"]

        # Only closed candle
        if not k["x"]:
            return

        ts = pd.to_datetime(k["T"], unit="ms")

        new_row = pd.DataFrame(
            [[k["o"], k["h"], k["l"], k["c"], k["v"]]],
            index=[ts],
            columns=["open","high","low","close","volume"]
        ).astype(float)

        # Drop oldest, add latest
        self.df = pd.concat([self.df.iloc[1:], new_row])

        # Recalculate indicators
        self.df.ta.macd(fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL, append=True)
        self.df[f"ema{EMA_FAST}"] = self.df["close"].ewm(span=EMA_FAST, adjust=False).mean()
        self.df[f"ema{EMA_SLOW}"] = self.df["close"].ewm(span=EMA_SLOW, adjust=False).mean()
        self.df["ATR"] = ta.atr(self.df["high"], self.df["low"], self.df["close"], length=ATR_PERIOD)
        self.df["MAX_ATR"] = self.df["ATR"].rolling(ATR_PERIOD).max()

        last = self.df.iloc[-1]
        prev = self.df.iloc[-2]

        macd = last[f"MACD_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}"]
        sig  = last[f"MACDs_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}"]
        pmac = prev[f"MACD_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}"]
        psig = prev[f"MACDs_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}"]

        atr = last["MAX_ATR"]
        price = last["close"]

        # ========== Combo-3 Signal Logic ==========
        signal = "HOLD"
        if macd > sig and pmac <= psig:
            signal = "BUY"
        elif macd < sig and pmac >= psig:
            signal = "SELL"

        # ========== FILTER CONDITIONS ==========
        # 1) ATR check (avoid weak candles)
        if atr <= MIN_ATR:
            return

        # 2) Ignore HOLD signals
        if signal == "HOLD":
            return

        # If reached here → Valid BUY/SELL detected
        self.final_signal = signal
        self.final_atr = atr
        self.final_price = price

        self.done = True
        ws.close()

    # --------------------------------------------------------
    def on_open(self, ws):
        print("🌐 One-Shot WebSocket Connected → Waiting for BUY/SELL...")

    def on_close(self, ws, *args):
        print("🔌 WebSocket Closed (Signal Found)")

    def on_error(self, ws, error):
        print("❌ WebSocket Error:", error)

    # --------------------------------------------------------
    # RUN UNTIL ONE VALID SIGNAL
    # --------------------------------------------------------
    def get_next_signal(self):

        self.ws = WebSocketApp(
            BINANCE_WS,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )

        # Wait until BUY/SELL found
        self.ws.run_forever(ping_interval=30, ping_timeout=10)

        # Return results
        return self.final_signal, self.final_price, self.final_atr