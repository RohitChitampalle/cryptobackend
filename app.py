from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from delta_service import DeltaService, place_order
from analysis_service import (
    get_historical_candles,
    merge_live_and_history,
    analyze_candles,
    get_product_names
)
from flask_cors import CORS

import threading
import traceback
import os
from kiteconnect import KiteConnect
from dotenv import load_dotenv

load_dotenv()

KITE_API_KEY = os.getenv("KITE_API_KEY")
KITE_API_SECRET = os.getenv("KITE_API_SECRET")

kite = KiteConnect(api_key=KITE_API_KEY)

app = Flask(__name__)
CORS(app)


#=======================================================
# KITE LOGIN
#=======================================================
@app.route("/api/kite/login", methods=["GET"])
def kite_login():
    try:
        login_url = kite.login_url()
        return jsonify({
            "success": True,
            "login_url": login_url
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    

@app.route("/api/kite/callback", methods=["GET"])
def kite_callback():

    print("====================================")
    print("KITE CALLBACK HIT")
    print("URL:", request.url)
    print("ARGS:", request.args.to_dict())
    print("====================================")

    request_token = request.args.get("request_token")
    status = request.args.get("status")
    action = request.args.get("action")

    if not request_token:
        return jsonify({
            "success": False,
            "error": "request_token not received",
            "status": status,
            "action": action,
            "received_params": request.args.to_dict()
        }), 400

    try:

        session_data = kite.generate_session(
            request_token,
            api_secret=KITE_API_SECRET
        )

        access_token = session_data["access_token"]

        app.config["KITE_ACCESS_TOKEN"] = access_token

        kite.set_access_token(access_token)

        print("KITE LOGIN SUCCESS")
        print("USER:", session_data.get("user_id"))

        return jsonify({
            "success": True,
            "message": "Zerodha login successful",
            "user_id": session_data.get("user_id"),
            "user_name": session_data.get("user_name"),
            "access_token_received": True
        })

    except Exception as e:

        print("KITE SESSION ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    
@app.route("/api/kite/profile", methods=["GET"])
def kite_profile():

    access_token = app.config.get("KITE_ACCESS_TOKEN")

    if not access_token:
        return jsonify({
            "success": False,
            "error": "Zerodha is not connected"
        }), 401

    try:
        kite.set_access_token(access_token)

        profile = kite.profile()

        return jsonify({
            "success": True,
            "data": profile
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    

@app.route("/api/kite/instruments", methods=["GET"])
def kite_instruments():

    print("====================================")
    print("KITE INSTRUMENTS HIT")

    access_token = app.config.get("KITE_ACCESS_TOKEN")

    print("TOKEN EXISTS:", bool(access_token))
    print("TOKEN LENGTH:", len(access_token) if access_token else 0)

    if not access_token:
        print("ERROR: KITE_ACCESS_TOKEN NOT FOUND")
        print("====================================")

        return jsonify({
            "success": False,
            "error": "Zerodha is not connected"
        }), 401

    try:

        kite.set_access_token(access_token)

        exchange = request.args.get("exchange")

        print("EXCHANGE:", exchange)

        if exchange:
            instruments = kite.instruments(exchange.upper())
        else:
            instruments = kite.instruments()

        print("INSTRUMENT COUNT:", len(instruments))
        print("====================================")

        return jsonify({
            "success": True,
            "exchange": exchange or "ALL",
            "count": len(instruments),
            "data": instruments
        })

    except Exception as e:

        print("KITE INSTRUMENT ERROR:", str(e))
        print("====================================")

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    
# =========================================================
# /api/kite/products endpoint that returns NSE + BSE + NFO + MCX, 
# removes duplicates, categorizes INDEX/EQUITY/FUTURES/OPTIONS
# =========================================================
@app.route("/api/kite/products", methods=["GET"])
def kite_products():

    access_token = app.config.get("KITE_ACCESS_TOKEN")

    if not access_token:
        return jsonify({
            "success": False,
            "error": "Zerodha is not connected"
        }), 401

    try:

        kite.set_access_token(access_token)

        # ==========================================
        # Query parameters
        # ==========================================

        exchange = request.args.get("exchange", "ALL").upper()
        search = request.args.get("search", "").strip().upper()
        category = request.args.get("category", "ALL").upper()

        # Pagination
        try:
            page = max(int(request.args.get("page", 1)), 1)
        except ValueError:
            page = 1

        try:
            limit = min(
                max(int(request.args.get("limit", 100)), 1),
                500
            )
        except ValueError:
            limit = 100

        # ==========================================
        # Supported exchanges
        # ==========================================

        valid_exchanges = [
            "NSE",
            "BSE",
            "NFO",
            "BFO",
            "MCX",
            "CDS"
        ]

        if exchange != "ALL" and exchange not in valid_exchanges:
            return jsonify({
                "success": False,
                "error": "Invalid exchange",
                "valid_exchanges": valid_exchanges
            }), 400

        # ==========================================
        # Get instruments
        # ==========================================

        if exchange == "ALL":

            instruments = []

            for ex in valid_exchanges:

                try:
                    data = kite.instruments(ex)
                    instruments.extend(data)

                except Exception as ex_error:

                    print(
                        f"Failed to load {ex} instruments:",
                        str(ex_error)
                    )

        else:

            instruments = kite.instruments(exchange)

        # ==========================================
        # Process instruments
        # ==========================================

        products = []

        for item in instruments:

            symbol = item.get("tradingsymbol", "")
            name = item.get("name", "")
            instrument_type = item.get("instrument_type", "")
            segment = item.get("segment", "")
            item_exchange = item.get("exchange", "")

            symbol_upper = symbol.upper()
            name_upper = name.upper()

            # ======================================
            # Determine category
            # ======================================

            if segment == "INDICES":

                product_category = "INDEX"

            elif instrument_type == "EQ":

                product_category = "EQUITY"

            elif instrument_type == "FUT":

                product_category = "FUTURES"

            elif instrument_type in ["CE", "PE"]:

                product_category = "OPTIONS"

            elif instrument_type == "COM":

                product_category = "COMMODITY"

            else:

                product_category = instrument_type or "OTHER"

            # ======================================
            # Search filter
            # ======================================

            if search:

                if (
                    search not in symbol_upper
                    and search not in name_upper
                ):
                    continue

            # ======================================
            # Category filter
            # ======================================

            if category != "ALL":

                if product_category != category:

                    continue

            # ======================================
            # Clean response
            # ======================================

            products.append({
                "symbol": symbol,
                "name": name,
                "exchange": item_exchange,
                "category": product_category,
                "instrument_type": instrument_type,
                "segment": segment,
                "instrument_token": item.get(
                    "instrument_token"
                ),
                "exchange_token": item.get(
                    "exchange_token"
                ),
                "expiry": item.get("expiry"),
                "strike": item.get("strike"),
                "lot_size": item.get("lot_size"),
                "tick_size": item.get("tick_size")
            })

        # ==========================================
        # Remove duplicates
        # ==========================================

        unique_products = {}

        for product in products:

            key = (
                product["exchange"],
                product["symbol"],
                product["instrument_type"],
                str(product["expiry"])
            )

            unique_products[key] = product

        products = list(unique_products.values())

        # ==========================================
        # Sort
        # ==========================================

        products.sort(
            key=lambda x: (
                x["exchange"],
                x["category"],
                x["symbol"]
            )
        )

        # ==========================================
        # Pagination
        # ==========================================

        total = len(products)

        start = (page - 1) * limit
        end = start + limit

        paginated_products = products[start:end]

        total_pages = (
            (total + limit - 1) // limit
            if total > 0
            else 0
        )

        # ==========================================
        # Response
        # ==========================================

        return jsonify({
            "success": True,
            "filters": {
                "exchange": exchange,
                "search": search,
                "category": category
            },
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages
            },
            "data": paginated_products
        })

    except Exception as e:

        print(
            "KITE PRODUCTS ERROR:",
            str(e)
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
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

#=========================================================
#CHART DATA
#=========================================================
@app.route("/api/kite/chart", methods=["GET"])
def kite_chart():

    access_token = app.config.get("KITE_ACCESS_TOKEN")

    if not access_token:
        return jsonify({
            "success": False,
            "error": "Zerodha is not connected"
        }), 401

    try:

        kite.set_access_token(access_token)

        # ==========================================
        # Query parameters
        # ==========================================

        exchange = request.args.get("exchange", "NSE").upper()
        symbol = request.args.get("symbol")

        interval = request.args.get(
            "interval",
            "5minute"
        )

        from_date = request.args.get("from")
        to_date = request.args.get("to")

        if not symbol:
            return jsonify({
                "success": False,
                "error": "symbol is required"
            }), 400

        # ==========================================
        # Supported intervals
        # ==========================================

        valid_intervals = [
            "minute",
            "3minute",
            "5minute",
            "10minute",
            "15minute",
            "30minute",
            "60minute",
            "day"
        ]

        if interval not in valid_intervals:
            return jsonify({
                "success": False,
                "error": "Invalid interval",
                "valid_intervals": valid_intervals
            }), 400

        # ==========================================
        # Find instrument
        # ==========================================

        instruments = kite.instruments(exchange)

        instrument = None

        for item in instruments:

            if (
                item.get("tradingsymbol", "").upper()
                == symbol.upper()
            ):
                instrument = item
                break

        if not instrument:

            return jsonify({
                "success": False,
                "error": "Instrument not found",
                "exchange": exchange,
                "symbol": symbol
            }), 404

        instrument_token = instrument.get(
            "instrument_token"
        )

        # ==========================================
        # Date range
        # ==========================================

        if from_date:
            try:
                from_dt = datetime.strptime(
                    from_date,
                    "%Y-%m-%d"
                )
            except ValueError:
                return jsonify({
                    "success": False,
                    "error": "Invalid 'from' date. Use YYYY-MM-DD"
                }), 400

        else:

            from_dt = datetime.now() - timedelta(days=5)

        if to_date:

            try:
                to_dt = datetime.strptime(
                    to_date,
                    "%Y-%m-%d"
                )

            except ValueError:

                return jsonify({
                    "success": False,
                    "error": "Invalid 'to' date. Use YYYY-MM-DD"
                }), 400

        else:

            to_dt = datetime.now()

        # ==========================================
        # Get historical candles
        # ==========================================

        candles = kite.historical_data(
            instrument_token,
            from_dt,
            to_dt,
            interval,
            continuous=False,
            oi=True
        )

        # ==========================================
        # Convert to chart format
        # ==========================================

        chart_data = []

        for candle in candles:

            chart_data.append({
                "timestamp": candle.get("date"),
                "open": candle.get("open"),
                "high": candle.get("high"),
                "low": candle.get("low"),
                "close": candle.get("close"),
                "volume": candle.get("volume", 0),
                "oi": candle.get("oi", 0)
            })

        # ==========================================
        # Response
        # ==========================================

        return jsonify({
            "success": True,

            "instrument": {
                "exchange": exchange,
                "symbol": symbol,
                "instrument_token": instrument_token,
                "name": instrument.get("name"),
                "instrument_type": instrument.get(
                    "instrument_type"
                )
            },

            "interval": interval,

            "from": from_dt.strftime("%Y-%m-%d"),

            "to": to_dt.strftime("%Y-%m-%d"),

            "count": len(chart_data),

            "data": chart_data
        })

    except Exception as e:

        print("====================================")
        print("KITE CHART ERROR")
        print(str(e))
        print("====================================")

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
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

@app.route("/test/candles", methods=["GET"])
def test_candles():

    symbol = request.args.get("symbol", "BTCUSD")
    timeframe = request.args.get("timeframe", "5m")

    try:

        candles = get_historical_candles(symbol, timeframe)

        return jsonify({
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "total_candles": len(candles),
            "first_candle": candles[0] if candles else None,
            "last_candle": candles[-1] if candles else None
        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500 
        
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

# @app.route("/api/analysis/btc", methods=["GET"])
# def btc_analysis():

#     try:

#         # -------------------------------------------------
#         # 1. Historical Candles
#         # -------------------------------------------------
#         history = get_historical_candles()

#         if not isinstance(history, list):
#             return jsonify({
#                 "success": False,
#                 "error": "Historical candles not returned as list"
#             }), 500

#         # -------------------------------------------------
#         # 2. Live Candle
#         # -------------------------------------------------
#         live = service.latest_candle

#         # -------------------------------------------------
#         # 3. Merge
#         # -------------------------------------------------
#         candles = merge_live_and_history(history, live)

#         # -------------------------------------------------
#         # 4. Validate
#         # -------------------------------------------------
#         if len(candles) < 50:
#             return jsonify({
#                 "success": False,
#                 "error": "Not enough candle data",
#                 "total_candles": len(candles)
#             }), 400

#         # -------------------------------------------------
#         # 5. Analysis
#         # -------------------------------------------------
#         result = analyze_candles(candles)

#         # -------------------------------------------------
#         # 6. Debug Logs
#         # -------------------------------------------------
#         print("\n" + "=" * 60)
#         print("BTC ANALYSIS")
#         print("=" * 60)
#         print("Historical Candles :", len(history))
#         print("Live Candle Exists :", live is not None)
#         print("Total Candles      :", len(candles))

#         if candles:
#             print("Last Close         :", candles[-1]["close"])

#         print("Signal             :", result["decision"]["action"])
#         print("Prediction         :", result["decision"]["prediction"])
#         print("=" * 60)

#         return jsonify({
#             "success": True,
#             "symbol": "BTCUSD",
#             "analysis": result,
#             "total_candles": len(candles)
#         })

#     except Exception as e:

#         traceback.print_exc()

#         return jsonify({
#             "success": False,
#             "error": str(e)
#         }), 500

@app.route("/api/analysis/<symbol>")
def get_analysis(symbol):

    timeframe = request.args.get("timeframe", "5m")

    candles = get_historical_candles(
        symbol,
        timeframe
    )

    result = analyze_candles(
        candles,
        timeframe,
        symbol
    )

    return jsonify(result)
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

@app.route("/webhook/analysis", methods=["POST"])
def webhook_analysis():
    global latest_analysis

    payload = request.json
    latest_analysis = payload

    return jsonify({
        "success": True
    })
@app.route("/api/products", methods=["GET"])
def products():

    try:

        products = get_product_names()

        return jsonify({
            "success": True,
            "count": len(products),
            "products": products
        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    

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