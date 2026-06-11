from flask import Flask, request, jsonify
from delta_service import DeltaService, place_order
from analysis_service import (
    get_historical_candles,
    merge_live_and_history,
    analyze_candles
)

import threading
import traceback

app = Flask(__name__)

# =========================================================
# START WEBSOCKET SERVICE
# =========================================================

service = DeltaService()


def start_ws():
    try:
        print("Starting Delta WebSocket...")
        service.start()
    except Exception as e:
        print("WebSocket Error:", e)
        traceback.print_exc()


threading.Thread(
    target=start_ws,
    daemon=True
).start()

# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/test", methods=["GET"])
def test():
    return jsonify({
        "success": True,
        "message": "Flask + WebSocket + Analysis backend running"
    })


# =========================================================
# LIVE MARKET DATA
# =========================================================

@app.route("/api/market/ticker", methods=["GET"])
def ticker():
    return jsonify({
        "success": True,
        "data": service.latest_ticker or {}
    })


@app.route("/api/market/trade", methods=["GET"])
def trade():
    return jsonify({
        "success": True,
        "data": service.latest_trade or {}
    })


@app.route("/api/market/candle", methods=["GET"])
def candle():
    return jsonify({
        "success": True,
        "data": service.latest_candle or {}
    })


# =========================================================
# BTC ANALYSIS
# =========================================================

@app.route("/api/analysis/btc", methods=["GET"])
def btc_analysis():

    try:

        # -------------------------------------------------
        # 1. Historical Candles
        # -------------------------------------------------
        history = get_historical_candles()

        if not isinstance(history, list):
            return jsonify({
                "success": False,
                "error": "Historical candles not returned as list"
            }), 500

        # -------------------------------------------------
        # 2. Live Candle
        # -------------------------------------------------
        live = service.latest_candle

        # -------------------------------------------------
        # 3. Merge
        # -------------------------------------------------
        candles = merge_live_and_history(history, live)

        # -------------------------------------------------
        # 4. Validate
        # -------------------------------------------------
        if len(candles) < 50:
            return jsonify({
                "success": False,
                "error": "Not enough candle data",
                "total_candles": len(candles)
            }), 400

        # -------------------------------------------------
        # 5. Analysis
        # -------------------------------------------------
        result = analyze_candles(candles)

        # -------------------------------------------------
        # 6. Debug Logs
        # -------------------------------------------------
        print("\n" + "=" * 60)
        print("BTC ANALYSIS")
        print("=" * 60)
        print("Historical Candles :", len(history))
        print("Live Candle Exists :", live is not None)
        print("Total Candles      :", len(candles))

        if candles:
            print("Last Close         :", candles[-1]["close"])

        print("Signal             :", result["decision"]["action"])
        print("Prediction         :", result["decision"]["prediction"])
        print("=" * 60)

        return jsonify({
            "success": True,
            "symbol": "BTCUSD",
            "analysis": result,
            "total_candles": len(candles)
        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# ORDER EXECUTION
# =========================================================

@app.route("/api/orders/punch", methods=["POST"])
def punch_order():

    try:

        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "Missing JSON body"
            }), 400

        payload = {
            "product_id": data["productId"],
            "size": data["quantity"],
            "side": data["side"],
            "order_type": data["orderType"]
        }

        if data["orderType"] == "limit_order":
            payload["limit_price"] = data["price"]

        result = place_order(payload)

        return jsonify({
            "success": True,
            "data": result
        })

    except KeyError as e:

        return jsonify({
            "success": False,
            "error": f"Missing field: {str(e)}"
        }), 400

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# BOT STATUS
# =========================================================

@app.route("/api/status", methods=["GET"])
def status():

    return jsonify({
        "success": True,
        "websocket_connected": service.latest_ticker is not None,
        "live_ticker": service.latest_ticker,
        "live_trade": service.latest_trade,
        "live_candle": service.latest_candle
    })


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    print("\nServer Started")
    print("API: http://localhost:8000")
    print("Health: http://localhost:8000/test\n")

    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    )