import pandas as pd
from analysis_service import (
    get_historical_candles,
    calculate_ema,
    calculate_rsi,
    calculate_atr
)

symbol = "SOLUSD"
timeframe = "5m"

candles = get_historical_candles(symbol, timeframe)

rows = []

for i in range(50, len(candles) - 3):

    subset = candles[:i + 1]

    closes = [c["close"] for c in subset]
    volumes = [c["volume"] for c in subset]

    ema9 = calculate_ema(closes, 9)
    ema20 = calculate_ema(closes, 20)

    rsi = calculate_rsi(closes)

    atr = calculate_atr(subset)

    momentum = closes[-1] - closes[-12]

    future_close = candles[i + 3]["close"]

    target = future_close - closes[-1]

    rows.append({
        "rsi": rsi,
        "ema9": ema9,
        "ema20": ema20,
        "atr": atr,
        "momentum": momentum,
        "volume": volumes[-1],
        "target": target
    })

df = pd.DataFrame(rows)

df.to_csv("training_data.csv", index=False)

print("Rows:", len(df))
print("training_data.csv created")