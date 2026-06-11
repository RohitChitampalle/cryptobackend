import os
import json
import time
import hmac
import hashlib
import requests
import threading
import websocket
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.india.delta.exchange"
WS_URL = "wss://public-socket.india.delta.exchange"

API_KEY = os.getenv("DELTA_API_KEY").strip()
API_SECRET = os.getenv("DELTA_API_SECRET").strip()

SYMBOL = "BTCUSD"


# =========================================================
# 1. REST: PLACE ORDER (your existing function improved)
# =========================================================
def place_order(payload):
    path = "/v2/orders"
    method = "POST"

    timestamp = str(int(time.time()))
    body = json.dumps(payload, separators=(",", ":"))

    message = method + timestamp + path + body

    signature = hmac.new(
        API_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "api-key": API_KEY,
        "timestamp": timestamp,
        "signature": signature,
        "Content-Type": "application/json",
        "User-Agent": "python-client"
    }

    response = requests.post(
        BASE_URL + path,
        headers=headers,
        data=body,
        timeout=5
    )

    return response.json()


# =========================================================
# 2. WEBSOCKET TRADING ENGINE
# =========================================================
class DeltaService:

    def __init__(self):
        self.ws = None

        # live market state
        self.latest_ticker = None
        self.latest_trade = None
        self.latest_candle = None

    # -----------------------------
    # WebSocket Handlers
    # -----------------------------
    def on_open(self, ws):
        print("✅ WebSocket Connected")

        subscribe_msg = {
            "type": "subscribe",
            "payload": {
                "channels": [
                    {"name": "ticker", "symbols": [SYMBOL]},
                    {"name": "trades", "symbols": [SYMBOL]},
                    {"name": "candlestick_1m", "symbols": [SYMBOL]},
                ]
            }
        }

        ws.send(json.dumps(subscribe_msg))
        print("📡 Subscribed to BTCUSD streams")

    def on_message(self, ws, message):
        try:
            data = json.loads(message)

            msg_type = data.get("type")

            # ---------------- ticker ----------------
            if msg_type == "ticker":
                self.latest_ticker = data

            # ---------------- trades ----------------
            elif msg_type == "trade":
                self.latest_trade = data

            # ---------------- candles ----------------
            elif "candlestick" in str(msg_type):
                self.latest_candle = data

        except Exception as e:
            print("Parse error:", e)

    def on_error(self, ws, error):
        print("❌ WS Error:", error)

    def on_close(self, ws, *args):
        print("⚠️ WebSocket closed. Reconnecting in 3s...")
        time.sleep(3)
        self.start()

    # -----------------------------
    # Start WebSocket in background
    # -----------------------------
    def start(self):
        self.ws = websocket.WebSocketApp(
            WS_URL,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )

        thread = threading.Thread(target=self.ws.run_forever)
        thread.daemon = True
        thread.start()

        print("🚀 DeltaService started")


# =========================================================
# 3. OPTIONAL HELPERS (for API layer)
# =========================================================
def get_latest_ticker(service: DeltaService):
    return service.latest_ticker


def get_latest_trade(service: DeltaService):
    return service.latest_trade


def get_latest_candle(service: DeltaService):
    return service.latest_candle