# ========================================================
# File: CDXMainbotxrp_StaticTP_SL_FixedQty_v5.py
# Purpose: Main trading bot (blockwise, readable). Uses one-shot
#          signal engine (Combo-3) and ATR-based TP/SL with fee_move.
# Notes:   - Uses IST timestamps (timezone-aware)
#          - Colored output per line: BUY=green, SELL=red, HOLD=yellow, status=blue
# ========================================================

# -------------------------
# BLOCK 0: Imports & Config
# -------------------------
import time
import math
import traceback
from datetime import datetime, timezone, timedelta
from typing import Tuple, Dict, Any

# --- FIX PYTHON PATH FOR SUPPORT FILES ---
import os, sys

# current file directory
THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# parent folder (Cloud_MainBot)
PARENT_DIR = os.path.dirname(THIS_DIR)

# support folder
SUPPORT_DIR = os.path.join(PARENT_DIR, "CDX_Support_File")

# Add to sys.path
if SUPPORT_DIR not in sys.path:
    sys.path.insert(0, SUPPORT_DIR)
# -----------------------------------------------------

# Exchange integration modules (must exist in your environment)
from CDXPOdata import get_xrp_data
from CDcreateworking import place_orders
from CDcreate_tp_sl import set_tpsl

# One-shot signal engine (must be the Option-1 engine file)
from xrp_Bye_Sell_atr_signal import DataEngine

# -------------------------
# BLOCK 1: Color & Time helpers
# -------------------------
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def ist_now_str() -> str:
    """Return timezone-aware IST 12-hour timestamp string."""
    now_utc = datetime.now(timezone.utc)
    ist = now_utc + timedelta(hours=5, minutes=30)
    return ist.strftime("%I:%M:%S %p")

def color_line(text: str, role: str = "info") -> None:
    """
    Print a colored line based on role:
    - 'buy'  -> green
    - 'sell' -> red
    - 'hold' -> yellow
    - otherwise -> blue
    """
    if role.lower() == "buy":
        col = GREEN
    elif role.lower() == "sell":
        col = RED
    elif role.lower() == "hold":
        col = YELLOW
    else:
        col = BLUE
    print(f"{col}[{ist_now_str()}] {text}{RESET}")

# -------------------------
# BLOCK 2: Bot Configuration
# -------------------------
SYMBOL = "XRPUSDT"
CDX_PAIR_ID = "B-XRP_USDT"
CDX_POSITION_ID = "b915ec98-8115-11f0-982a-67144ee3c0bc"

# Trading / staking
FIXED_QUANTITY = 3.5        # fixed for now (dynamic qty commented)
CDX_LEVERAGE = 60
BASE_STEP = 15
STEP_INCREMENT = 5
PROFIT_TARGET = 500

# ATR & multipliers
ATR_PERIOD = 14
BASE_SL_MULT = 1.5
BASE_TP_MULT = 2.5
RR_RATIO = BASE_TP_MULT / BASE_SL_MULT  # 1.666...

# Fee & FX (as requested)
FX = 96
ROE = 0.07

# Volatility filter
MIN_MAX_ATR_ENTRY = 0.005

# Timeouts & retries
MAX_API_RETRIES = 5
RETRY_DELAY = 5
SET_TPSL_TIMEOUT = 120
POLL_INTERVAL = 5
REQUIRED_CLOSED_CHECKS = 5

# -------------------------
# BLOCK 3: Globals (state)
# -------------------------
CDX_active_position: float = 0.0
CDX_pos_entry_price: float = 0.0
CDX_pos_take_profit: float = 0.0
CDX_pos_stop_loss: float = 0.0
xrp_current_price: float = 0.0

# Running trackers
CDX_cumulative_pnl: float = 0.0
cycle_step: int = 1

# -------------------------
# BLOCK 4: Exchange helpers
# -------------------------
def update_position_globals(is_initial_check: bool = False) -> bool:
    """
    Query exchange (get_xrp_data) and update globals.
    Retries internally; raises on persistent failure.
    """
    global CDX_active_position, CDX_pos_entry_price, CDX_pos_take_profit, CDX_pos_stop_loss, xrp_current_price

    for attempt in range(1, MAX_API_RETRIES + 1):
        try:
            data = get_xrp_data()
            CDX_active_position = float(data.get("active_pos", 0.0))
            CDX_pos_entry_price = round(float(data.get("avg_price", 0.0)), 4)
            CDX_pos_take_profit = round(float(data.get("take_profit", 0.0)), 4)
            CDX_pos_stop_loss = round(float(data.get("stop_loss", 0.0)), 4)
            xrp_current_price = round(float(data.get("XRPCurentPrice", 0.0)), 4)

            role = "info"
            status = "ACTIVE" if abs(CDX_active_position) > 0.00001 else "NO_POS"
            color_line(f"{'INIT' if is_initial_check else 'DATA'} | ActivePos: {CDX_active_position} | Entry: {CDX_pos_entry_price} | TP: {CDX_pos_take_profit} | SL: {CDX_pos_stop_loss} | Price: {xrp_current_price} | Status:{status}", role=status.lower())
            return True

        except Exception as e:
            color_line(f"get_xrp_data failed (attempt {attempt}/{MAX_API_RETRIES}): {e}", role="info")
            time.sleep(RETRY_DELAY)
            if attempt == MAX_API_RETRIES:
                raise
    return False

def place_market_order_and_confirm(side: str) -> bool:
    """
    Place a market order. Wait briefly and confirm an active position exists.
    """
    order_payload = [{
        "side": side.lower(),
        "pair": CDX_PAIR_ID,
        "quantity": FIXED_QUANTITY,
        "leverage": CDX_LEVERAGE,
        "order_type": "market_order",
    }]

    color_line(f"Placing Market Order -> {order_payload}", role=side.lower())
    for attempt in range(1, MAX_API_RETRIES + 1):
        try:
            resp = place_orders(order_payload)
            color_line(f"Order response: {resp}", role="info")
            time.sleep(20)  # settle time
            update_position_globals()
            if abs(CDX_active_position) > 0.00001:
                color_line("Market order confirmed (active position detected).", role=side.lower())
                return True
            else:
                color_line("No active position detected after order; retrying.", role="info")
                time.sleep(RETRY_DELAY)
        except Exception as e:
            color_line(f"place_orders failed (attempt {attempt}): {e}", role="info")
            traceback.print_exc()
            time.sleep(RETRY_DELAY)
    color_line("Failed to place/confirm market order.", role="info")
    return False

# -------------------------
# BLOCK 5: Fee & TP/SL Calculations
# -------------------------
def calculate_fee_move_from_fixed_qty(price: float, fixed_qty: float, leverage: float, fx: float, roe: float) -> float:
    """
    Fee_move formula (as requested):
    1) Fee_margin = (fixed_qty × price × FX ) × 0.05% × 1.18
    2) Bet_amount = (( fixed_qty × price × FX ) / leverage ) + Fee_margin
    3) fee = roe × bet_amount
    4) fee_move = fee / fixed_qty / fx
    """
    fee_margin = (fixed_qty * price * fx) * 0.0005 * 1.18     # 0.05% -> 0.0005
    bet_amount = ((fixed_qty * price * fx) / leverage) + fee_margin
    fee = roe * bet_amount
    if fixed_qty == 0 or fx == 0:
        return 0.0001
    fee_move = fee / fixed_qty / fx
    return fee_move

def compute_tpsl_from_atr_and_fee(entry_price: float, atr_value: float, side: str) -> Tuple[float, float, Dict[str, Any]]:
    """
    Compute TP & SL using ATR multipliers and fee_move.
    Rules:
      - if atr > 0.08 -> sl_mult = 1.0
      - if 0.05 <= atr <= 0.08 -> sl_mult = 1.5
      - else -> sl_mult = 1.5
      tp_mult = sl_mult * RR_RATIO
      tp_move includes fee_move
    Returns (tp_price, sl_price, details)
    """
    if atr_value is None or math.isnan(atr_value):
        raise ValueError("Invalid ATR for TP/SL calculation")

    if atr_value > 0.08:
        sl_mult = 1.0
    elif 0.05 <= atr_value <= 0.08:
        sl_mult = 1.5
    else:
        sl_mult = 1.5

    tp_mult = sl_mult * RR_RATIO
    fee_move = calculate_fee_move_from_fixed_qty(entry_price, FIXED_QUANTITY, CDX_LEVERAGE, FX, ROE)

    sl_move = sl_mult * atr_value
    tp_move = (tp_mult * atr_value) + fee_move

    if side.upper() == "BUY":
        tp_price = round(entry_price + tp_move, 4)
        sl_price = round(entry_price - sl_move, 4)
    elif side.upper() == "SELL":
        tp_price = round(entry_price - tp_move, 4)
        sl_price = round(entry_price + sl_move, 4)
    else:
        raise ValueError("Invalid side for TP/SL")

    details = {
        "atr": atr_value,
        "sl_mult": sl_mult,
        "tp_mult": tp_mult,
        "sl_move": sl_move,
        "tp_move": tp_move,
        "fee_move": fee_move
    }
    return tp_price, sl_price, details

# -------------------------
# BLOCK 6: TP/SL Placement & Verification
# -------------------------
def attempt_set_tpsl(tp_price: float, sl_price: float) -> bool:
    """
    Call set_tpsl and return True on success (no exception).
    """
    try:
        set_tpsl(CDX_POSITION_ID, tp_price, sl_price)
        color_line(f"Called set_tpsl -> TP: {tp_price}, SL: {sl_price}", role="info")
        return True
    except Exception as e:
        color_line(f"set_tpsl error: {e}", role="info")
        traceback.print_exc()
        return False

def verify_and_retry_tpsl(side: str, tp_price: float, sl_price: float) -> bool:
    """
    Verify TP/SL are present on exchange; retry missing ones until timeout.
    """
    color_line(f"Verifying TP/SL (timeout {SET_TPSL_TIMEOUT}s)...", role="info")
    start = time.time()
    while time.time() - start < SET_TPSL_TIMEOUT:
        try:
            update_position_globals()
        except Exception as e:
            color_line(f"get_xrp_data error during TP/SL verification: {e}", role="info")
            time.sleep(POLL_INTERVAL)
            continue

        tp_missing = abs(CDX_pos_take_profit) < 0.00001
        sl_missing = abs(CDX_pos_stop_loss) < 0.00001

        if not tp_missing and not sl_missing:
            color_line(f"TP ({CDX_pos_take_profit}) and SL ({CDX_pos_stop_loss}) confirmed.", role="info")
            return True

        # Attempt to set missing ones
        tp_to_send = tp_price if tp_missing else 0.0
        sl_to_send = sl_price if sl_missing else 0.0
        target = "BOTH" if tp_missing and sl_missing else ("TP" if tp_missing else "SL")

        color_line(f"Missing -> TP:{tp_missing}, SL:{sl_missing}. Retrying set ({target})", role="info")
        attempt_set_tpsl(tp_to_send, sl_to_send)
        time.sleep(POLL_INTERVAL)

    color_line("TP/SL verification timed out.", role="info")
    return False

# -------------------------
# BLOCK 7: Position Monitoring
# -------------------------
def wait_for_position_close() -> bool:
    """
    Wait until exchange reports no active position and confirm it REQUIRED_CLOSED_CHECKS times.
    """
    global CDX_active_position
    color_line("Waiting for position to close (5x confirmation)...", role="info")
    consecutive = 0
    while consecutive < REQUIRED_CLOSED_CHECKS:
        try:
            update_position_globals()
        except Exception as e:
            color_line(f"get_xrp_data failed while waiting for close: {e}", role="info")
            consecutive = 0
            time.sleep(POLL_INTERVAL)
            continue

        if abs(CDX_active_position) < 0.00001:
            consecutive += 1
            color_line(f"Closure confirmation {consecutive}/{REQUIRED_CLOSED_CHECKS}", role="info")
        else:
            if consecutive > 0:
                color_line("Position re-detected active; resetting confirmation count", role="info")
            consecutive = 0
        time.sleep(POLL_INTERVAL)
    color_line("Position confirmed closed.", role="info")
    return True

# -------------------------
# BLOCK 8: Main Execution Flow
# -------------------------
def main():
    color_line("--- BOT STARTUP ---", role="info")
    while True:
        try:
            # 1) Check current position
            try:
                update_position_globals(is_initial_check=True)
            except Exception as e:
                color_line(f"Initial get_xrp_data failed: {e}", role="info")
                time.sleep(10)
                continue

            # If non-zero, wait until closed (skip engine)
            if abs(CDX_active_position) > 0.00001:
                color_line("Active position detected on startup. Monitoring until closed.", role="info")
                wait_for_position_close()
                continue

            # 2) Position zero -> start one-shot engine
            color_line("Position zero confirmed. Starting one-shot live engine for next valid signal...", role="info")
            engine = DataEngine()
            try:
                engine.load_historical(limit=500)
            except Exception as e:
                color_line(f"Failed to load historical candles: {e}", role="info")
                time.sleep(10)
                continue

            try:
                signal, sig_price, sig_atr = engine.get_next_signal()
            except Exception as e:
                color_line(f"One-shot engine error: {e}", role="info")
                time.sleep(10)
                continue

            if signal not in ("BUY", "SELL"):
                color_line(f"Engine returned non-trade signal ({signal}). Restarting cycle.", role="info")
                time.sleep(3)
                continue

            color_line(f"Received signal -> {signal} | Price: {sig_price} | ATR: {sig_atr}", role=signal.lower())

            # 3) Place market order based on signal
            placed = place_market_order_and_confirm(signal)
            if not placed:
                color_line("Market order placement/confirmation failed. Restarting loop.", role="info")
                time.sleep(5)
                continue

            # 4) Compute TP & SL using ATR + fee_move
            entry_price = CDX_pos_entry_price if CDX_pos_entry_price and CDX_pos_entry_price > 0 else float(sig_price)
            atr_for_levels = sig_atr if sig_atr is not None else MIN_MAX_ATR_ENTRY

            try:
                tp_price, sl_price, details = compute_tpsl_from_atr_and_fee(entry_price, atr_for_levels, signal)
            except Exception as e:
                color_line(f"TP/SL computation error: {e} -> falling back to static offsets", role="info")
                # fallback static offsets (previous behavior)
                tp_price = round(entry_price + 0.02, 4) if signal == "BUY" else round(entry_price - 0.02, 4)
                sl_price = round(entry_price - 0.0085, 4) if signal == "BUY" else round(entry_price + 0.0085, 4)
                details = {"fallback": True}

            color_line(f"TP: {tp_price} | SL: {sl_price} | details: {details}", role=signal.lower())

            # 5) Place TP & SL
            attempt_set_tpsl(tp_price, sl_price)

            # 6) Verify & retry missing TP/SL
            verify_and_retry_tpsl(signal, tp_price, sl_price)

            # 7) Monitor position until closed
            color_line("Monitoring active position until closed...", role="info")
            wait_for_position_close()

            # 8) Repeat cycle
            color_line("Trade cycle complete. Preparing next cycle.", role="info")
            time.sleep(3)

        except Exception as e:
            color_line(f"UNHANDLED ERROR in main loop: {e}", role="info")
            traceback.print_exc()
            color_line("Sleeping 60s before retrying...", role="info")
            time.sleep(60)
            continue

# -------------------------
# BLOCK 9: Script Entry
# -------------------------
if __name__ == "__main__":
    main()