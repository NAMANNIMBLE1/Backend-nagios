from fastapi import APIRouter, HTTPException, Query
from typing import Literal
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
    CombinedSeriesResponse,
    SeriesPoint,
)

router = APIRouter(prefix="/predict", tags=["Prediction"])

GranularityT = Literal["5min", "hourly", "6hour", "daily"]

RESAMPLE_RULE = {
    "5min":  "5min",
    "hourly": "1h",
    "6hour":  "6h",
    "daily":  "1D",
}

TS_FORMAT = {
    "5min":  "%d %b %H:%M",
    "hourly": "%d %b %H:%M",
    "6hour":  "%d %b %H:%M",
    "daily":  "%d %b",
}


def _require_cache() -> dict:
    if not model_cache.is_ready():
        raise HTTPException(
            status_code=503,
            detail="Model not ready — training is still running. Retry in a moment.",
        )
    return model_cache.get_cache()


def _get_forecast_df(cache: dict, days: int) -> tuple:
    if days == cache["days_ahead"]:
        return cache["forecast_df"], cache["days_ahead"]

    # forecast() returns a plain DataFrame, not a tuple
    result = forecast(cache["model"], cache["scaler"], cache["data"], days_ahead=days)
    if isinstance(result, tuple):
        forecast_df, days_ahead = result
    else:
        forecast_df = result
        days_ahead  = days          # use the requested days

    return forecast_df, days_ahead


# GET /predict/metrics

@router.get("/metrics", response_model=ModelMetricsResponse, summary="Model evaluation metrics")
def get_model_metrics():
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
    try:
        cache = _require_cache()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "target_col"  : cache["data"]["target_col"],
        "total_points": len(cache["y_test"]),
        "cached_at"   : model_cache.get_cached_at(),
        "series"      : [
            {"index": i, "actual": round(float(a), 4), "predicted": round(float(p), 4)}
            for i, (a, p) in enumerate(zip(cache["y_test"], cache["y_pred"]))
        ],
    }


# GET /predict/run

@router.get("/run", summary="Full pipeline result from cache")
def run_pipeline():
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


# GET /predict/combined?granularity=hourly&days=7
# Returns historical actuals + future forecast resampled to requested granularity.
# This is the main endpoint for the dashboard chart.

@router.get("/combined", response_model=CombinedSeriesResponse, summary="Historical + forecast combined")
def get_combined(
    days: int = Query(default=7, ge=1, le=30, description="Forecast days ahead"),
    granularity: GranularityT = Query(default="hourly", description="5min | hourly | 6hour | daily"),
):
    try:
        cache                   = _require_cache()
        forecast_df, days_ahead = _get_forecast_df(cache, days)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    data       = cache["data"]
    target_col = data["target_col"]
    df_full    = data["df_full"]
    df_model   = data["df_model"]
    pred_col   = f"{target_col}_pred"
    rule       = RESAMPLE_RULE[granularity]
    ts_fmt     = TS_FORMAT[granularity]

    # ── Historical: average across all hosts, then resample ──────────────
    hist = df_full[["check_time"]].copy()
    hist[target_col] = df_model[target_col].reindex(df_full.index).values
    hist = hist.dropna(subset=[target_col])
    hist = hist.set_index("check_time")[target_col]
    hist = hist.resample(rule).mean().dropna()

    # ── Forecast: resample ────────────────────────────────────────────────
    fcast = forecast_df.copy()
    fcast["timestamp"] = pd.to_datetime(fcast["timestamp"])
    fcast = fcast.set_index("timestamp")[pred_col]
    fcast = fcast.resample(rule).mean().dropna()

    # More decimals for fine granularity, fewer for coarse
    decimals = 2 if granularity == "5min" else 1 if granularity == "hourly" else 0

    return CombinedSeriesResponse(
        target_col     = target_col,
        granularity    = granularity,
        days_ahead     = days_ahead,
        forecast_start = str(forecast_df["timestamp"].min()),
        cached_at      = model_cache.get_cached_at(),
        historical     = [
            SeriesPoint(timestamp=ts.strftime(ts_fmt), value=round(float(v), decimals))
            for ts, v in hist.items()
        ],
        forecast       = [
            SeriesPoint(timestamp=ts.strftime(ts_fmt), value=round(float(v), decimals))
            for ts, v in fcast.items()
        ],
    )