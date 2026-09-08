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

# ==========================================
# LIVE PRICES FOR ALL SYMBOLS
# ==========================================
latest_prices = {}
subscribed_symbols = []


# ==========================================
# LOAD ALL LIVE SYMBOLS
# ==========================================
def load_symbols():
    global subscribed_symbols

    try:
        response = requests.get(
            "https://api.india.delta.exchange/v2/products",
            timeout=10
        )

        response.raise_for_status()

        products = response.json().get("result", [])

        subscribed_symbols = [
            p["symbol"]
            for p in products
            if (
                p.get("contract_type") == "perpetual_futures"
                and p.get("state") == "live"
            )
        ]

        print(
            f"✅ Loaded {len(subscribed_symbols)} live symbols"
        )

    except Exception as e:
        print("❌ Symbol Load Error:", e)
        subscribed_symbols = ["BTCUSD"]


# ==========================================
# PLACE ORDER
# ==========================================
def place_order(payload):

    path = "/v2/orders"
    method = "POST"

    timestamp = str(int(time.time()))

    body = json.dumps(
        payload,
        separators=(",", ":")
    )

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
        timeout=10
    )

    return response.json()


# ==========================================
# WEBSOCKET SERVICE
# ==========================================
class DeltaService:

    def __init__(self):

        self.ws = None

        self.latest_ticker = None
        self.latest_trade = None
        self.latest_candle = None

    # ======================================
    # CONNECTED
    # ======================================
    def on_open(self, ws):

        print("✅ WebSocket Connected")

        if not subscribed_symbols:
            load_symbols()

        subscribe_msg = {
            "type": "subscribe",
            "payload": {
                "channels": [
                    {
                        "name": "ticker",
                        "symbols": subscribed_symbols
                    },
                    {
                        "name": "trades",
                        "symbols": subscribed_symbols
                    },
                    {
                        "name": "candlestick_1m",
                        "symbols": subscribed_symbols
                    }
                ]
            }
        }

        ws.send(json.dumps(subscribe_msg))

        print(
            f"📡 Subscribed to {len(subscribed_symbols)} symbols"
        )

    # ======================================
    # MESSAGE
    # ======================================
    def on_message(self, ws, message):

        try:

            data = json.loads(message)

            msg_type = data.get("type")

            # -------------------------------
            # TICKER
            # -------------------------------
            if msg_type == "ticker":

                self.latest_ticker = data

                try:

                    symbol = data.get("sy")

                    price = data.get("sp")

                    if symbol and price:

                        latest_prices[symbol] = float(price)

                except Exception as e:
                    print(
                        "Ticker Parse Error:",
                        e
                    )

            # -------------------------------
            # TRADE
            # -------------------------------
            elif msg_type in ["trade", "trades"]:

                self.latest_trade = data

                try:

                    symbol = data.get("sy")

                    price = data.get("p")

                    if symbol and price:

                        latest_prices[symbol] = float(price)

                except:
                    pass

            # -------------------------------
            # CANDLE
            # -------------------------------
            elif "candlestick" in str(msg_type):

                self.latest_candle = data

        except Exception as e:

            print("Parse Error:", e)

    # ======================================
    # ERROR
    # ======================================
    def on_error(self, ws, error):

        print("❌ WS Error:", error)

    # ======================================
    # CLOSE
    # ======================================
    def on_close(self, ws, *args):

        print(
            "⚠️ WebSocket closed. Reconnecting..."
        )

        time.sleep(3)

        self.start()

    # ======================================
    # START
    # ======================================
    def start(self):

        self.ws = websocket.WebSocketApp(
            WS_URL,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )

        thread = threading.Thread(
            target=self.ws.run_forever
        )

        thread.daemon = True
        thread.start()

        print("🚀 DeltaService started")


# ==========================================
# HELPERS
# ==========================================
def get_latest_ticker(service):
    return service.latest_ticker


def get_latest_trade(service):
    return service.latest_trade


def get_latest_candle(service):
    return service.latest_candle