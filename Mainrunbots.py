import threading
import sys
import os

# Add bot folders to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, "ProjectDEX"))
sys.path.append(os.path.join(current_dir, "Xrp_bot_code"))

# Import the main functions
# from DEXMainbotxrp import main as dex_main   # ❌ DEX main commented
from CDXMainbotxrp import main as cdx_main

# Threads for parallel execution
"""
def run_dex_bot():
    try:
        dex_main()
    except Exception as e:
        print(f"❌ DEX Bot Error: {e}")
"""

def run_cdx_bot():
    try:
        cdx_main()
    except Exception as e:
        print(f"❌ CDX Bot Error: {e}")

if __name__ == "__main__":
    # t1 = threading.Thread(target=run_dex_bot)   # ❌ DEX thread commented
    t2 = threading.Thread(target=run_cdx_bot)

    # t1.start()   # ❌ DEX thread start commented
    t2.start()

    # t1.join()   # ❌ DEX thread join commented
    t2.join()