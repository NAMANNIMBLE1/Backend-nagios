"""
predict.py
~~~~~~~~~~
Model training + forecasting helpers.
The `train()` function is now called from training_service.py.
`forecast()` is used both there and lazily in the API routes.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from app.controllers.data_processing import prediction_tabular_data
from config.get_config import get_config

logger = logging.getLogger(__name__)


# ── training ──────────────────────────────────────────────────────────────────

def train(X, y):
    """Time-ordered train/test split → fit LinearRegression → return artefacts."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    scaler  = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test  = scaler.transform(X_test)

    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    logger.info(
        "\n── Model Evaluation ──────────────────────\n"
        "   MAE  : %.4f\n   RMSE : %.4f\n   R²   : %.4f\n"
        "──────────────────────────────────────────",
        mean_absolute_error(y_test, y_pred),
        np.sqrt(mean_squared_error(y_test, y_pred)),
        float(r2_score(y_test, y_pred)),
    )

    return model, scaler, y_test, y_pred


# ── forecasting ───────────────────────────────────────────────────────────────

def forecast(model, scaler, data: dict, days_ahead: int = 7) -> pd.DataFrame:
    """
    Auto-regressive 5-minute-step forecast for `days_ahead` days.

    Returns a DataFrame with columns [timestamp, {target_col}_pred].
    """
    df_full      = data["df_full"]
    df_model     = data["df_model"]
    feature_cols = data["feature_names"]
    target_col   = data["target_col"]

    steps     = (days_ahead * 24 * 60) // 5
    last_time = df_full["check_time"].max()
    history   = list(df_model[target_col].values)

    timestamps: list  = []
    predictions: list = []

    for i in range(1, steps + 1):
        next_time = last_time + pd.Timedelta(minutes=5 * i)

        row = {
            "time_index"  : (next_time - df_full["check_time"].min()).total_seconds() / 3600,
            "hour"        : next_time.hour,
            "minute"      : next_time.minute,
            "day_of_week" : next_time.dayofweek,
            "day_of_month": next_time.day,
            "is_weekend"  : int(next_time.dayofweek >= 5),
            "is_warning"  : 0,
            "is_critical" : 0,
            f"{target_col}_lag1"        : history[-1]  if len(history) >= 1  else np.nan,
            f"{target_col}_lag3"        : history[-3]  if len(history) >= 3  else np.nan,
            f"{target_col}_lag6"        : history[-6]  if len(history) >= 6  else np.nan,
            f"{target_col}_lag12"       : history[-12] if len(history) >= 12 else np.nan,
            f"{target_col}_roll_mean_12": np.mean(history[-12:]),
            f"{target_col}_roll_std_12" : np.std(history[-12:]),
            f"{target_col}_roll_mean_36": np.mean(history[-36:]),
            f"{target_col}_roll_max_12" : np.max(history[-12:]),
        }

        X_future = np.array([[row.get(c, 0.0) for c in feature_cols]])
        y_hat    = model.predict(scaler.transform(X_future))[0]

        history.append(y_hat)
        timestamps.append(next_time)
        predictions.append(y_hat)

    forecast_df = pd.DataFrame({
        "timestamp":           timestamps,
        f"{target_col}_pred":  predictions,
    })

    logger.info(
        "[Forecast] steps=%d (%d days)  range=%.2f → %.2f",
        len(forecast_df), days_ahead,
        float(forecast_df[f"{target_col}_pred"].min()),
        float(forecast_df[f"{target_col}_pred"].max()),
    )

    return forecast_df


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    host    = sys.argv[1] if len(sys.argv) > 1 else None
    service = sys.argv[2] if len(sys.argv) > 2 else None

    data = prediction_tabular_data(host=host, service=service)
    X, y = data["X"], data["y"]

    model, scaler, y_test, y_pred = train(X, y)

    config        = get_config()
    forecast_days = int(config.get("FORECAST_DAYS", 7))
    forecast_df   = forecast(model, scaler, data, days_ahead=forecast_days)

    forecast_df.to_csv("forecast_output.csv", index=False)
    logger.info("Forecast saved → forecast_output.csv")
