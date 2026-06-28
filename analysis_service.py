import time
import requests

BASE_URL = "https://api.india.delta.exchange"


# =====================================================
# FETCH HISTORICAL CANDLES
# =====================================================
# def get_historical_candles():
#     end = int(time.time())

#     # Last 4 hours of 1-minute candles
#     start = end - (4 * 60 * 60)

#     url = f"{BASE_URL}/v2/history/candles"

#     params = {
#         "symbol": "BTCUSD",
#         "resolution": "1m",
#         "start": start,
#         "end": end
#     }

#     try:
#         response = requests.get(url, params=params, timeout=10)
#         data = response.json()

#         candles = data.get("result", [])

#         normalized = []

#         for c in candles:
#             normalized.append({
#                 "open": float(c["open"]),
#                 "high": float(c["high"]),
#                 "low": float(c["low"]),
#                 "close": float(c["close"]),
#                 "volume": float(c.get("volume", 0))
#             })

#         return normalized

#     except Exception as e:
#         print("Error:", e)
#         return []

def get_historical_candles(symbol, timeframe):

    end = int(time.time())

    timeframe_map = {
        "5m": 2 * 24 * 60 * 60,
        "15m": 5 * 24 * 60 * 60,
        "30m": 10 * 24 * 60 * 60,
        "1h": 20 * 24 * 60 * 60,
        "4h": 120 * 24 * 60 * 60,
        "1d": 365 * 24 * 60 * 60
    }

    resolution_map = {
        "5m": "5",
        "15m": "15",
        "30m": "30",
        "1h": "60",
        "4h": "240",
        "1d": "1D"
    }

    start = end - timeframe_map.get(timeframe, 2 * 24 * 60 * 60)

    params = {
            "symbol": symbol,
    "resolution": timeframe,
    "start": start,
    "end": end
    } 
     
     

    print(
        f"Fetching candles | Symbol={symbol} | Timeframe={timeframe}"
    )

    try:
        response = requests.get(
            f"{BASE_URL}/v2/history/candles",
            params=params,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        candles = [
            {
                "open": float(c["open"]),
                "high": float(c["high"]),
                "low": float(c["low"]),
                "close": float(c["close"]),
                "volume": float(c.get("volume", 0))
            }
            for c in data.get("result", [])
        ]

        print(f"Received {len(candles)} candles")

        return candles

    except Exception as e:
     print("=" * 80)
     print("ERROR:", e)

    if 'response' in locals():
        print("STATUS:", response.status_code)
        print("URL:", response.url)
        print("BODY:", response.text)

    print("=" * 80)

    return []
    
def get_product_names():

    url = "https://api.india.delta.exchange/v2/products"

    response = requests.get(url, timeout=10)
    response.raise_for_status()

    data = response.json()

    products = data.get("result", [])

    return [
        p["symbol"]
        for p in products
        if (
            p.get("contract_type") == "perpetual_futures"
            and p.get("state") == "live"
        )
    ]

    
# =====================================================
# SIMPLE EMA
# =====================================================
def calculate_ema(prices, period):
    if len(prices) < period:
        return None

    multiplier = 2 / (period + 1)

    ema = sum(prices[:period]) / period

    for price in prices[period:]:
        ema = ((price - ema) * multiplier) + ema

    return ema


def merge_live_and_history(history, live):

    candles = []

    if history:
        candles.extend(history)

    if live and isinstance(live, dict):

        normalized_live = {
            "open": float(live.get("o", live.get("open", 0))),
            "high": float(live.get("h", live.get("high", 0))),
            "low": float(live.get("l", live.get("low", 0))),
            "close": float(live.get("c", live.get("close", 0))),
            "volume": float(live.get("v", live.get("volume", 0)))
        }

        candles.append(normalized_live)

    return candles

# =====================================================
# RSI
# =====================================================
def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50

    gains = []
    losses = []

    for i in range(1, period + 1):
        change = closes[-i] - closes[-i - 1]

        if change > 0:
            gains.append(change)
        else:
            losses.append(abs(change))

    avg_gain = sum(gains) / period if gains else 0.0001
    avg_loss = sum(losses) / period if losses else 0.0001

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


# =====================================================
# ATR
# =====================================================
def calculate_atr(candles, period=14):
    if len(candles) < period + 1:
        return 20

    true_ranges = []

    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        prev_close = candles[i - 1]["close"]

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )

        true_ranges.append(tr)

    return sum(true_ranges[-period:]) / period


# =====================================================
# MAIN ANALYSIS
# =====================================================
# def analyze_candles(candles):

#     if len(candles) < 50:
#         return {
#             "status": "HOLD",
#             "message": "Not enough candle data"
#         }

#     closes = [c["close"] for c in candles]
#     volumes = [c["volume"] for c in candles]

#     current_price = closes[-1]

#     # -------------------------
#     # EMA
#     # -------------------------
#     ema9 = calculate_ema(closes, 9)
#     ema20 = calculate_ema(closes, 20)

#     # -------------------------
#     # RSI
#     # -------------------------
#     rsi = calculate_rsi(closes)

#     # -------------------------
#     # VOLUME SPIKE
#     # -------------------------
#     avg_volume = sum(volumes[-20:]) / 20
#     current_volume = volumes[-1]

#     volume_spike = current_volume > (avg_volume * 1.5)

#     # -------------------------
#     # ATR
#     # -------------------------
#     atr = calculate_atr(candles)

#     # -------------------------
#     # MOMENTUM (Last 5 min)
#     # -------------------------
#     momentum = closes[-1] - closes[-6]

#     # -------------------------
#     # SIGNAL
#     # -------------------------
#     signal = "HOLD"
#     reason = []

#     if ema9 > ema20:
#         reason.append("EMA9 above EMA20")

#     if ema9 < ema20:
#         reason.append("EMA9 below EMA20")

#     if rsi > 55:
#         reason.append("Bullish RSI")

#     if rsi < 45:
#         reason.append("Bearish RSI")

#     if volume_spike:
#         reason.append("Volume spike detected")

#     if (
#         ema9 > ema20 and
#         rsi > 55 and
#         momentum > 0
#     ):
#         signal = "BUY"

#     elif (
#         ema9 < ema20 and
#         rsi < 45 and
#         momentum < 0
#     ):
#         signal = "SELL"

#     # -------------------------
#     # TARGET & SL
#     # -------------------------
#     target = None
#     stop_loss = None

#     if signal == "BUY":
#         target = round(current_price + (atr * 1.5), 2)
#         stop_loss = round(current_price - atr, 2)

#     elif signal == "SELL":
#         target = round(current_price - (atr * 1.5), 2)
#         stop_loss = round(current_price + atr, 2)

#     # -------------------------
#     # NEXT 5 MIN PREDICTION
#     # -------------------------
#     if signal == "BUY":
#         prediction = "Higher probability of upside in next 5 minutes"

#     elif signal == "SELL":
#         prediction = "Higher probability of downside in next 5 minutes"

#     else:
#         prediction = "Sideways movement expected"

#     return {
#         "market_summary": {
#             "price": current_price,
#             "ema9": round(ema9, 2),
#             "ema20": round(ema20, 2),
#             "rsi": round(rsi, 2),
#             "atr": round(atr, 2),
#             "momentum": round(momentum, 2)
#         },

#         "decision": {
#             "action": signal,
#             "prediction": prediction,
#             "reason": reason
#         },

#         "trade": {
#             "entry": current_price,
#             "target": target,
#             "stop_loss": stop_loss
#         }
#     }


# def analyze_candles(candles):

#     if len(candles) < 50:
#         return {
#             "status": "HOLD",
#             "message": "Not enough candle data"
#         }

#     closes = [float(c["close"]) for c in candles]
#     volumes = [float(c.get("volume", 0)) for c in candles]

#     current_price = closes[-1]

#     # ==========================================
#     # EMA
#     # ==========================================

#     ema9 = calculate_ema(closes, 9)
#     ema20 = calculate_ema(closes, 20)

#     # ==========================================
#     # RSI
#     # ==========================================

#     rsi = calculate_rsi(closes)

#     # ==========================================
#     # ATR
#     # ==========================================

#     atr = calculate_atr(candles)

#     # ==========================================
#     # MOMENTUM (5 MINUTES)
#     # ==========================================

#     momentum = closes[-1] - closes[-6]

#     # ==========================================
#     # VOLUME SPIKE
#     # ==========================================

#     avg_volume = sum(volumes[-20:]) / 20
#     current_volume = volumes[-1]

#     volume_spike = current_volume > (avg_volume * 1.5)

#     # ==========================================
#     # SIGNAL GENERATION
#     # ==========================================

#     signal = "HOLD"
#     reason = []

#     if ema9 > ema20:
#         reason.append("EMA9 above EMA20")
#     else:
#         reason.append("EMA9 below EMA20")

#     if rsi > 55:
#         reason.append("Bullish RSI")

#     elif rsi < 45:
#         reason.append("Bearish RSI")

#     if volume_spike:
#         reason.append("Volume spike detected")

#     if (
#         ema9 > ema20 and
#         rsi > 55 and
#         momentum > 0
#     ):
#         signal = "BUY"

#     elif (
#         ema9 < ema20 and
#         rsi < 45 and
#         momentum < 0
#     ):
#         signal = "SELL"

#     # ==========================================
#     # PREDICTION
#     # ==========================================

#     if signal == "BUY":
#         prediction = "Higher probability of upside in next 5 minutes"

#     elif signal == "SELL":
#         prediction = "Higher probability of downside in next 5 minutes"

#     else:
#         prediction = "Sideways movement expected"

#     # ==========================================
#     # SUPPORT / RESISTANCE
#     # ==========================================

#     lookback = min(120, len(closes))

#     recent_closes = closes[-lookback:]

#     support = min(recent_closes)
#     resistance = max(recent_closes)

#     potential_upside = round(resistance - current_price, 2)
#     potential_downside = round(current_price - support, 2)

#     # ==========================================
#     # TARGETS
#     # ==========================================

#     safe_target = None
#     medium_target = None
#     aggressive_target = None
#     maximum_expected_target = None
#     stop_loss = None

#     if signal == "BUY":

#         stop_loss = round(current_price - atr, 2)

#         safe_target = round(current_price + (atr * 1.5), 2)

#         medium_target = round(current_price + (atr * 3), 2)

#         aggressive_target = round(current_price + (atr * 5), 2)

#         maximum_expected_target = round(resistance, 2)

#     elif signal == "SELL":

#         stop_loss = round(current_price + atr, 2)

#         safe_target = round(current_price - (atr * 1.5), 2)

#         medium_target = round(current_price - (atr * 3), 2)

#         aggressive_target = round(current_price - (atr * 5), 2)

#         maximum_expected_target = round(support, 2)

#     # ==========================================
#     # RETURN
#     # ==========================================

#     return {
#         "market_summary": {
#             "price": round(current_price, 2),
#             "ema9": round(ema9, 2),
#             "ema20": round(ema20, 2),
#             "rsi": round(rsi, 2),
#             "atr": round(atr, 2),
#             "momentum": round(momentum, 2)
#         },

#         "decision": {
#             "action": signal,
#             "prediction": prediction,
#             "reason": reason
#         },

#         "trade": {
#             "entry": round(current_price, 2),
#             "stop_loss": stop_loss,

#             "targets": {
#                 "safe": safe_target,
#                 "medium": medium_target,
#                 "aggressive": aggressive_target
#             },

#             "maximum_expected_target": maximum_expected_target
#         },

#         "market_structure": {
#             "support": round(support, 2),
#             "resistance": round(resistance, 2)
#         },

#         "potential_move": {
#             "upside_points": potential_upside,
#             "downside_points": potential_downside
#         }
#     }

# def analyze_candles(candles):

#     if len(candles) < 100:
#         return {
#             "status": "HOLD",
#             "message": "Not enough candle data"
#         }

#     closes = [float(c["close"]) for c in candles]
#     volumes = [float(c.get("volume", 0)) for c in candles]

#     current_price = closes[-1]

#     # ==========================================
#     # EMA (1-HOUR TREND)
#     # ==========================================

#     ema9 = calculate_ema(closes, 9)
#     ema20 = calculate_ema(closes, 20)

#     # ==========================================
#     # RSI
#     # ==========================================

#     rsi = calculate_rsi(closes)

#     # ==========================================
#     # ATR
#     # ==========================================

#     atr = calculate_atr(candles)

#     # ==========================================
#     # MOMENTUM (60 MINUTES)
#     # ==========================================

#     momentum = closes[-1] - closes[-61]

#     # ==========================================
#     # VOLUME SPIKE
#     # ==========================================

#     avg_volume = sum(volumes[-20:]) / 20
#     current_volume = volumes[-1]

#     volume_spike = current_volume > (avg_volume * 1.5)

#     # ==========================================
#     # SIGNAL GENERATION
#     # ==========================================

#     signal = "HOLD"
#     reason = []

#     if ema9 > ema20:
#         reason.append("EMA9 above EMA20")
#     else:
#         reason.append("EMA9 below EMA20")

#     if rsi > 55:
#         reason.append("Bullish RSI")

#     elif rsi < 45:
#         reason.append("Bearish RSI")

#     if volume_spike:
#         reason.append("Volume spike detected")

#     if (
#         ema9 > ema20 and
#         rsi > 55 and
#         momentum > 0
#     ):
#         signal = "BUY"

#     elif (
#         ema9 < ema20 and
#         rsi < 45 and
#         momentum < 0
#     ):
#         signal = "SELL"

#     # ==========================================
#     # PREDICTION
#     # ==========================================

#     if signal == "BUY":
#         prediction = "Higher probability of upside in next 1 hour"

#     elif signal == "SELL":
#         prediction = "Higher probability of downside in next 1 hour"

#     else:
#         prediction = "Sideways movement expected over next 1 hour"

#     # ==========================================
#     # SUPPORT / RESISTANCE (4 HOURS)
#     # ==========================================

#     lookback = min(240, len(closes))

#     recent_closes = closes[-lookback:]

#     support = min(recent_closes)
#     resistance = max(recent_closes)

#     potential_upside = round(resistance - current_price, 2)
#     potential_downside = round(current_price - support, 2)

#     # ==========================================
#     # TARGETS
#     # ==========================================

#     safe_target = None
#     medium_target = None
#     aggressive_target = None
#     maximum_expected_target = None
#     stop_loss = None

#     if signal == "BUY":

#         stop_loss = round(current_price - (atr * 1.5), 2)

#         safe_target = round(current_price + (atr * 3), 2)

#         medium_target = round(current_price + (atr * 5), 2)

#         aggressive_target = round(current_price + (atr * 8), 2)

#         maximum_expected_target = round(resistance, 2)

#     elif signal == "SELL":

#         stop_loss = round(current_price + (atr * 1.5), 2)

#         safe_target = round(current_price - (atr * 3), 2)

#         medium_target = round(current_price - (atr * 5), 2)

#         aggressive_target = round(current_price - (atr * 8), 2)

#         maximum_expected_target = round(support, 2)

#     # ==========================================
#     # RETURN
#     # ==========================================

#     return {
#         "market_summary": {
#             "price": round(current_price, 2),
#             "ema9": round(ema9, 2),
#             "ema20": round(ema20, 2),
#             "rsi": round(rsi, 2),
#             "atr": round(atr, 2),
#             "momentum_1h": round(momentum, 2)
#         },

#         "decision": {
#             "action": signal,
#             "prediction": prediction,
#             "reason": reason
#         },

#         "trade": {
#             "entry": round(current_price, 2),
#             "stop_loss": stop_loss,

#             "targets": {
#                 "safe": safe_target,
#                 "medium": medium_target,
#                 "aggressive": aggressive_target
#             },

#             "maximum_expected_target": maximum_expected_target
#         },

#         "market_structure": {
#             "support": round(support, 2),
#             "resistance": round(resistance, 2)
#         },

#         "potential_move": {
#             "upside_points": potential_upside,
#             "downside_points": potential_downside
#         }
#     }

def analyze_candles(candles, timeframe="5m"):

    if len(candles) < 100:
        return {
            "status": "HOLD",
            "message": "Not enough candle data"
        }

    closes = [float(c["close"]) for c in candles]
    volumes = [float(c.get("volume", 0)) for c in candles]

    current_price = closes[-1]

    ema9 = calculate_ema(closes, 9)
    ema20 = calculate_ema(closes, 20)

    rsi = calculate_rsi(closes)
    atr = calculate_atr(candles)

    # ===================================
    # Dynamic Momentum
    # ===================================

    momentum_map = {
        "5m": 12,
        "15m": 12,
        "30m": 12,
        "1h": 24,
        "4h": 12,
        "1d": 7
    }

    momentum_period = momentum_map.get(timeframe, 12)

    if len(closes) > momentum_period:
        momentum = closes[-1] - closes[-momentum_period]
    else:
        momentum = 0

    # ===================================
    # Volume
    # ===================================

    avg_volume = sum(volumes[-20:]) / 20
    current_volume = volumes[-1]

    volume_spike = current_volume > avg_volume * 1.5

    # ===================================
    # Trend
    # ===================================

    trend = "SIDEWAYS"

    if ema9 > ema20:
        trend = "BULLISH"

    elif ema9 < ema20:
        trend = "BEARISH"

    # ===================================
    # Signal
    # ===================================

    signal = "HOLD"
    reason = []

    if ema9 > ema20:
        reason.append("EMA9 above EMA20")

    if ema9 < ema20:
        reason.append("EMA9 below EMA20")

    if rsi > 55:
        reason.append("Bullish RSI")

    if rsi < 45:
        reason.append("Bearish RSI")

    if volume_spike:
        reason.append("Volume Spike")

    if ema9 > ema20 and rsi > 55 and momentum > 0:
        signal = "BUY"

    elif ema9 < ema20 and rsi < 45 and momentum < 0:
        signal = "SELL"

    # ===================================
    # Support / Resistance
    # ===================================

    support = min(closes[-100:])
    resistance = max(closes[-100:])

    # ===================================
    # Targets
    # ===================================

    stop_loss = None
    target1 = None
    target2 = None
    target3 = None

    if signal == "BUY":

        stop_loss = round(current_price - (atr * 1.5), 2)

        target1 = round(current_price + (atr * 2), 2)
        target2 = round(current_price + (atr * 4), 2)
        target3 = round(current_price + (atr * 6), 2)

    elif signal == "SELL":

        stop_loss = round(current_price + (atr * 1.5), 2)

        target1 = round(current_price - (atr * 2), 2)
        target2 = round(current_price - (atr * 4), 2)
        target3 = round(current_price - (atr * 6), 2)

    return {

        "timeframe": timeframe,

        "market_summary": {
            "price": round(current_price, 2),
            "trend": trend,
            "ema9": round(ema9, 2),
            "ema20": round(ema20, 2),
            "rsi": round(rsi, 2),
            "atr": round(atr, 2),
            "momentum": round(momentum, 2)
        },

        "decision": {
            "action": signal,
            "reason": reason
        },

        "market_structure": {
            "support": round(support, 2),
            "resistance": round(resistance, 2)
        },

        "trade": {
            "entry": round(current_price, 2),
            "stop_loss": stop_loss,
            "target_1": target1,
            "target_2": target2,
            "target_3": target3
        }
    }