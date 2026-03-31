from fastapi import APIRouter, HTTPException, Query
import numpy as np
import pandas as pd

from app.cache import model_cache
from app.controllers.predict import forecast
from app.schemas.response import (
    ModelMetricsResponse,
    ForecastResponse,
    ForecastPoint,
    ForecastSummaryResponse,
    DailyAverage,
)

router = APIRouter(prefix="/predict", tags=["Prediction"])


def _require_cache() -> dict:
    """Raise 503 if the model hasn't been trained yet."""
    if not model_cache.is_ready():
        raise HTTPException(
            status_code = 503,
            detail      = "Model not ready — training is still running. Retry in a moment.",
        )
    return model_cache.get_cache()


def _get_forecast_df(cache: dict, days: int) -> tuple:
    """
    Reuse the cached forecast when days matches what was trained,
    otherwise re-run forecast() from the cached model (no DB hit).
    """
    if days == cache["days_ahead"]:
        return cache["forecast_df"], cache["days_ahead"]

    forecast_df, days_ahead = forecast(
        cache["model"], cache["scaler"], cache["data"], days_ahead=days
    )
    return forecast_df, days_ahead


# GET /predict/metrics

@router.get("/metrics", response_model=ModelMetricsResponse, summary="Model evaluation metrics")
def get_model_metrics():
    """MAE, RMSE and R² on the 20% held-out test set."""
    try:
        cache   = _require_cache()
        metrics = cache["metrics"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ModelMetricsResponse(
        target_col = cache["data"]["target_col"],
        mae        = metrics["mae"],
        rmse       = metrics["rmse"],
        r2         = metrics["r2"],
        train_rows = metrics["train_rows"],
        test_rows  = metrics["test_rows"],
    )


# GET /predict/forecast?days=7

@router.get("/forecast", response_model=ForecastResponse, summary="Full 5-min step forecast")
def get_forecast(
    days: int = Query(default=7, ge=1, le=30, description="Days to forecast ahead")
):
    """Every 5-minute predicted value for the next N days."""
    try:
        cache                   = _require_cache()
        forecast_df, days_ahead = _get_forecast_df(cache, days)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    target_col = cache["data"]["target_col"]
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
        cache                   = _require_cache()
        forecast_df, days_ahead = _get_forecast_df(cache, days)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    target_col  = cache["data"]["target_col"]
    pred_col    = f"{target_col}_pred"

    forecast_df = forecast_df.copy()
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
    """Actual and predicted pairs from the cached test split."""
    try:
        cache = _require_cache()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    y_test     = cache["y_test"]
    y_pred     = cache["y_pred"]
    target_col = cache["data"]["target_col"]

    return {
        "target_col"  : target_col,
        "total_points": len(y_test),
        "cached_at"   : model_cache.get_cached_at(),
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

@router.get("/run", summary="Full pipeline result from cache")
def run_pipeline():
    """Returns full metrics + forecast summary from the last training run."""
    try:
        cache = _require_cache()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    target_col  = cache["data"]["target_col"]
    pred_col    = f"{target_col}_pred"
    metrics     = cache["metrics"]
    days_ahead  = cache["days_ahead"]

    forecast_df = cache["forecast_df"].copy()
    forecast_df["date"] = pd.to_datetime(forecast_df["timestamp"]).dt.date
    daily = forecast_df.groupby("date")[pred_col].agg(["mean", "min", "max"]).reset_index()

    return {
        "target_col": target_col,
        "cached_at" : model_cache.get_cached_at(),
        "metrics"   : metrics,
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