from fastapi import APIRouter, HTTPException, Query
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from app.controllers.data_processing import prediction_tabular_data
from app.controllers.predict import train, forecast
from app.schemas.response import (
    ModelMetricsResponse,
    ForecastResponse,
    ForecastPoint,
    ForecastSummaryResponse,
    DailyAverage,
)
from config.get_config import get_config

router = APIRouter(prefix="/predict", tags=["Prediction"])


def _get_trained_model(days_ahead: int = 7):
    """Shared helper — loads data, trains model, returns everything."""
    data                          = prediction_tabular_data()
    X, y                          = data["X"], data["y"]
    model, scaler, y_test, y_pred = train(X, y)

    # forecast() may return (df, days) or just df depending on your controller version
    result = forecast(model, scaler, data, days_ahead=days_ahead)
    if isinstance(result, tuple):
        forecast_df, days_ahead = result
    else:
        forecast_df = result
        days_ahead  = int(days_ahead)

    return data, model, scaler, y_test, y_pred, forecast_df, days_ahead



# GET /predict/metrics

@router.get("/metrics", response_model=ModelMetricsResponse, summary="Model evaluation metrics")
def get_model_metrics():
    """MAE, RMSE and R² on the 20% held-out test set."""
    try:
        data                          = prediction_tabular_data()
        X, y                          = data["X"], data["y"]
        model, scaler, y_test, y_pred = train(X, y)

        split = int(len(X) * 0.8)

        return ModelMetricsResponse(
            target_col = data["target_col"],
            mae        = round(float(mean_absolute_error(y_test, y_pred)), 4),
            rmse       = round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 4),
            r2         = round(float(r2_score(y_test, y_pred)), 4),
            train_rows = split,
            test_rows  = len(X) - split,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# GET /predict/forecast?days=7

@router.get("/forecast", response_model=ForecastResponse, summary="Full 5-min step forecast")
def get_forecast(
    days: int = Query(default=7, ge=1, le=30, description="Days to forecast ahead")
):
    """Every 5-minute predicted value for the next N days."""
    try:
        data, model, scaler, y_test, y_pred, forecast_df, days_ahead = _get_trained_model(days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    target_col = data["target_col"]
    pred_col   = f"{target_col}_pred"

    return ForecastResponse(
        target_col     = target_col,
        days_ahead     = days_ahead,
        total_steps    = len(forecast_df),
        forecast_start = str(forecast_df["timestamp"].min()),
        forecast_end   = str(forecast_df["timestamp"].max()),
        predicted_min  = round(float(forecast_df[pred_col].min()), 4),
        predicted_max  = round(float(forecast_df[pred_col].max()), 4),
        predicted_mean = round(float(forecast_df[pred_col].mean()), 4),
        forecast       = [
            ForecastPoint(
                timestamp       = str(row["timestamp"]),
                predicted_value = round(float(row[pred_col]), 4),
            )
            for _, row in forecast_df.iterrows()
        ],
    )



# GET /predict/summary?days=7

@router.get("/summary", response_model=ForecastSummaryResponse, summary="Daily aggregated forecast")
def get_forecast_summary(
    days: int = Query(default=7, ge=1, le=30, description="Days to forecast ahead")
):
    """One row per day with avg/min/max — lighter payload for dashboards."""
    try:
        data, model, scaler, y_test, y_pred, forecast_df, days_ahead = _get_trained_model(days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    target_col = data["target_col"]
    pred_col   = f"{target_col}_pred"

    forecast_df["date"] = pd.to_datetime(forecast_df["timestamp"]).dt.date
    daily = forecast_df.groupby("date")[pred_col].agg(["mean", "min", "max"]).reset_index()

    return ForecastSummaryResponse(
        target_col     = target_col,
        days_ahead     = days_ahead,
        forecast_start = str(forecast_df["timestamp"].min()),
        forecast_end   = str(forecast_df["timestamp"].max()),
        predicted_min  = round(float(forecast_df[pred_col].min()), 4),
        predicted_max  = round(float(forecast_df[pred_col].max()), 4),
        predicted_mean = round(float(forecast_df[pred_col].mean()), 4),
        daily_averages = [
            DailyAverage(
                date      = str(row["date"]),
                avg_value = round(float(row["mean"]), 4),
                min_value = round(float(row["min"]), 4),
                max_value = round(float(row["max"]), 4),
            )
            for _, row in daily.iterrows()
        ],
    )



# GET /predict/actual-vs-predicted

@router.get("/actual-vs-predicted", summary="Actual vs predicted on test set")
def get_actual_vs_predicted():
    """Actual and predicted pairs from test split — for accuracy chart."""
    try:
        data                          = prediction_tabular_data()
        X, y                          = data["X"], data["y"]
        model, scaler, y_test, y_pred = train(X, y)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "target_col"  : data["target_col"],
        "total_points": len(y_test),
        "series"      : [
            {
                "index"    : i,
                "actual"   : round(float(a), 4),
                "predicted": round(float(p), 4),
            }
            for i, (a, p) in enumerate(zip(y_test, y_pred))
        ],
    }



# GET /predict/run

@router.get("/run", summary="Full pipeline run using config FORECAST_DAYS")
def run_pipeline():
    """Train + forecast in one shot using FORECAST_DAYS from .env config."""
    try:
        config     = get_config()
        days_ahead = int(config["FORECAST_DAYS"])
        data, model, scaler, y_test, y_pred, forecast_df, days_ahead = _get_trained_model(days_ahead)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    target_col = data["target_col"]
    pred_col   = f"{target_col}_pred"

    forecast_df["date"] = pd.to_datetime(forecast_df["timestamp"]).dt.date
    daily = forecast_df.groupby("date")[pred_col].agg(["mean", "min", "max"]).reset_index()

    return {
        "target_col": target_col,
        "metrics": {
            "mae" : round(float(mean_absolute_error(y_test, y_pred)), 4),
            "rmse": round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 4),
            "r2"  : round(float(r2_score(y_test, y_pred)), 4),
        },
        "forecast_summary": {
            "days_ahead"    : days_ahead,
            "forecast_start": str(forecast_df["timestamp"].min()),
            "forecast_end"  : str(forecast_df["timestamp"].max()),
            "predicted_min" : round(float(forecast_df[pred_col].min()), 4),
            "predicted_max" : round(float(forecast_df[pred_col].max()), 4),
            "predicted_mean": round(float(forecast_df[pred_col].mean()), 4),
        },
        "daily_averages": [
            {
                "date"     : str(row["date"]),
                "avg_value": round(float(row["mean"]), 4),
                "min_value": round(float(row["min"]), 4),
                "max_value": round(float(row["max"]), 4),
            }
            for _, row in daily.iterrows()
        ],
    }