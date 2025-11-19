from flask import Flask
import threading
import sys
import os

app = Flask(__name__)

# Add bot folders to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, "ProjectDEX"))
sys.path.append(os.path.join(current_dir, "Xrp_bot_code"))

# Import the main function
from CDXMainbotxrp import main as cdx_main

def run_cdx_bot():
    try:
        cdx_main()
    except Exception as e:
        print(f"❌ CDX Bot Error: {e}")

@app.route('/')
def health_check():
    return 'Bot is running', 200

def run_flask():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    # Start the bot in a separate thread
    t2 = threading.Thread(target=run_cdx_bot)
    t2.start()

    # Run Flask server in the main thread
    run_flask()

    t2.join()