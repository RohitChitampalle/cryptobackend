import pandas as pd
import joblib

from sklearn.ensemble import GradientBoostingRegressor

df = pd.read_csv("training_data.csv")

features = [
    "rsi",
    "ema9",
    "ema20",
    "atr",
    "momentum",
    "volume"
]

X = df[features]
y = df["target"]

model = GradientBoostingRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=4,
    random_state=42
)

model.fit(X, y)

joblib.dump(
    model,
    "gbm_model.pkl"
)

print("Model Saved")