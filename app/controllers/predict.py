import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
# predict.py — line 8
from app.controllers.data_processing import prediction_tabular_data
from config.get_config import get_config


def train(X, y):
    # Time-ordered split — no shuffle (important for time-series)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    scaler  = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test  = scaler.transform(X_test)

    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    print("\n── Model Evaluation ──────────────────────")
    print(f"   MAE  : {mean_absolute_error(y_test, y_pred):.4f}")
    print(f"   RMSE : {np.sqrt(mean_squared_error(y_test, y_pred)):.4f}")
    print(f"   R²   : {r2_score(y_test, y_pred):.4f}")
    print("──────────────────────────────────────────\n")

    return model, scaler, y_test, y_pred

# next days forecasting (default value 7 days)
def forecast(model, scaler, data: dict, days_ahead: int = 7):
    df_full      = data["df_full"]
    df_model     = data["df_model"]
    feature_cols = data["feature_names"]
    target_col   = data["target_col"]

    steps      = (days_ahead * 24 * 60) // 5
    last_time  = df_full["check_time"].max()
    history    = list(df_model[target_col].values)

    timestamps  = []
    predictions = []

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
        "timestamp"          : timestamps,
        f"{target_col}_pred" : predictions,
    })

    print(f"[INFO] Forecast steps  : {len(forecast_df)}  ({days_ahead} days)")
    print(f"[INFO] Forecast range  : {forecast_df[f'{target_col}_pred'].min():.2f}"
          f" → {forecast_df[f'{target_col}_pred'].max():.2f}")

    return forecast_df



def plot(data: dict, y_test, y_pred, forecast_df: pd.DataFrame):
    df_full    = data["df_full"]
    df_model   = data["df_model"]
    target_col = data["target_col"]

    fig, axes = plt.subplots(2, 1, figsize=(16, 10))

    # ── Actual vs Predicted (test set) ──
    ax1 = axes[0]
    ax1.plot(y_test, label="Actual",    color="steelblue", linewidth=1.5)
    ax1.plot(y_pred, label="Predicted", color="orangered", linewidth=1.5, linestyle="--")
    ax1.set_title("Actual vs Predicted — Test Set")
    ax1.set_xlabel("Sample index")
    ax1.set_ylabel(target_col)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # ── Historical + Forecast ──
    ax2 = axes[1]
    ax2.plot(df_full["check_time"],
             df_model[target_col].reindex(df_full.index),
             label="Historical", color="steelblue", linewidth=1.2)
    ax2.plot(forecast_df["timestamp"],
             forecast_df[f"{target_col}_pred"],
             label=f"Forecast ({days_ahead} days)",
             color="darkorange", linewidth=1.5, linestyle="--")
    ax2.axvline(x=df_full["check_time"].max(),
                color="gray", linestyle=":", label="Forecast start")
    ax2.set_title(f"Power Usage Forecast — {target_col}")
    ax2.set_xlabel("Time")
    ax2.set_ylabel(target_col)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("forecast_output.png", dpi=150)
    plt.show()
    print("[INFO] Plot saved → forecast_output.png")


if __name__ == "__main__":
    # ── Step 1: Load preprocessed data ──
    data = prediction_tabular_data()
    X, y = data["X"], data["y"]

    # ── Step 2: Train ──
    model, scaler, y_test, y_pred = train(X, y)

    # ── Step 3: Forecast ──
    config = get_config()
    forecast_days = int(config["FORECAST_DAYS"])
    days_ahead  =   forecast_days # change to 10 for 10-day forecast
    forecast_df = forecast(model, scaler, data, days_ahead=days_ahead)

    # ── Step 4: Plot ──
    plot(data, y_test, y_pred, forecast_df)

    # ── Step 5: Save ──
    forecast_df.to_csv("forecast_output.csv", index=False)
    print("[INFO] Forecast saved → forecast_output.csv")