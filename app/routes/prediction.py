"""
routes/prediction.py
~~~~~~~~~~~~~~~~~~~~
Prediction and forecast endpoints.

All routes accept ?host= and ?service= — training is triggered lazily on
first access for each (host, service) pair.
"""

import logging
from typing import Literal, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.cache.model_cache import model_cache
from app.controllers.predict import forecast
from app.schemas.response import (
    CombinedSeriesResponse,
    DailyAverage,
    ForecastPoint,
    ForecastResponse,
    ForecastSummaryResponse,
    ModelMetricsResponse,
    SeriesPoint,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predict", tags=["Prediction"])

GranularityT = Literal["5min", "hourly", "6hour", "daily"]

RESAMPLE_RULE = {"5min": "5min", "hourly": "1h", "6hour": "6h", "daily": "1D"}
TS_FORMAT = {
    "5min": "%d %b %H:%M",
    "hourly": "%d %b %H:%M",
    "6hour": "%d %b %H:%M",
    "daily": "%d %b",
}


# ── shared helpers ────────────────────────────────────────────────────────────


def _ensure_cache(host: Optional[str], service: Optional[str]) -> dict:
    if not model_cache.is_ready(host, service):
        logger.info("[Route] Cache miss — training host=%s service=%s", host, service)
        from app.services.training_service import run_training_pipeline

        try:
            run_training_pipeline(host=host, service=service)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Training error: {exc}")

    return model_cache.get_cache(host, service)


def _get_forecast_df(
    cache: dict, host: Optional[str], service: Optional[str], days: int
):
    if days == cache["days_ahead"]:
        return cache["forecast_df"], cache["days_ahead"]

    result = forecast(cache["model"], cache["scaler"], cache["data"], days_ahead=days)
    if isinstance(result, tuple):
        forecast_df, days_ahead = result
    else:
        forecast_df = result
        days_ahead = days

    return forecast_df, days_ahead


# ── GET /predict/metrics ──────────────────────────────────────────────────────


@router.get(
    "/metrics",
    response_model=ModelMetricsResponse,
    summary="Model evaluation metrics for a host / service",
)
def get_model_metrics(
    host: Optional[str] = Query(default=None, description="Host alias"),
    service: Optional[str] = Query(default=None, description="Service name"),
):
    cache = _ensure_cache(host, service)
    metrics = cache["metrics"]

    return ModelMetricsResponse(
        host=host,
        service=service,
        target_col=cache["data"]["target_col"],
        mae=metrics["mae"],
        rmse=metrics["rmse"],
        r2=metrics["r2"],
        train_rows=metrics["train_rows"],
        test_rows=metrics["test_rows"],
    )


# ── GET /predict/forecast ─────────────────────────────────────────────────────


@router.get(
    "/forecast",
    response_model=ForecastResponse,
    summary="Full 5-min step forecast for a host / service",
)
def get_forecast(
    host: Optional[str] = Query(default=None, description="Host alias"),
    service: Optional[str] = Query(default=None, description="Service name"),
    days: int = Query(default=7, ge=1, le=30, description="Days ahead"),
):
    cache = _ensure_cache(host, service)
    forecast_df, days_ahead = _get_forecast_df(cache, host, service, days)
    target_col = cache["data"]["target_col"]
    pred_col = f"{target_col}_pred"

    return ForecastResponse(
        host=host,
        service=service,
        target_col=target_col,
        days_ahead=days_ahead,
        total_steps=len(forecast_df),
        forecast_start=str(forecast_df["timestamp"].min()),
        forecast_end=str(forecast_df["timestamp"].max()),
        predicted_min=round(float(forecast_df[pred_col].min()), 4),
        predicted_max=round(float(forecast_df[pred_col].max()), 4),
        predicted_mean=round(float(forecast_df[pred_col].mean()), 4),
        forecast=[
            ForecastPoint(
                timestamp=str(row["timestamp"]),
                predicted_value=round(float(row[pred_col]), 4),
            )
            for _, row in forecast_df.iterrows()
        ],
    )


# ── GET /predict/summary ──────────────────────────────────────────────────────


@router.get(
    "/summary",
    response_model=ForecastSummaryResponse,
    summary="Daily aggregated forecast for a host / service",
)
def get_forecast_summary(
    host: Optional[str] = Query(default=None, description="Host alias"),
    service: Optional[str] = Query(default=None, description="Service name"),
    days: int = Query(default=7, ge=1, le=30, description="Days ahead"),
):
    cache = _ensure_cache(host, service)
    forecast_df, days_ahead = _get_forecast_df(cache, host, service, days)
    target_col = cache["data"]["target_col"]
    pred_col = f"{target_col}_pred"

    forecast_df = forecast_df.copy()
    forecast_df["date"] = pd.to_datetime(forecast_df["timestamp"]).dt.date
    daily = (
        forecast_df.groupby("date")[pred_col].agg(["mean", "min", "max"]).reset_index()
    )

    return ForecastSummaryResponse(
        host=host,
        service=service,
        target_col=target_col,
        days_ahead=days_ahead,
        forecast_start=str(forecast_df["timestamp"].min()),
        forecast_end=str(forecast_df["timestamp"].max()),
        predicted_min=round(float(forecast_df[pred_col].min()), 4),
        predicted_max=round(float(forecast_df[pred_col].max()), 4),
        predicted_mean=round(float(forecast_df[pred_col].mean()), 4),
        daily_averages=[
            DailyAverage(
                date=str(row["date"]),
                avg_value=round(float(row["mean"]), 4),
                min_value=round(float(row["min"]), 4),
                max_value=round(float(row["max"]), 4),
            )
            for _, row in daily.iterrows()
        ],
    )


# ── GET /predict/actual-vs-predicted ─────────────────────────────────────────


@router.get(
    "/actual-vs-predicted",
    summary="Actual vs predicted on test set for a host / service",
)
def get_actual_vs_predicted(
    host: Optional[str] = Query(default=None, description="Host alias"),
    service: Optional[str] = Query(default=None, description="Service name"),
):
    cache = _ensure_cache(host, service)
    return {
        "host": host,
        "service": service,
        "target_col": cache["data"]["target_col"],
        "total_points": len(cache["y_test"]),
        "cached_at": model_cache.get_cached_at(host, service),
        "series": [
            {"index": i, "actual": round(float(a), 4), "predicted": round(float(p), 4)}
            for i, (a, p) in enumerate(zip(cache["y_test"], cache["y_pred"]))
        ],
    }


# ── GET /predict/run ──────────────────────────────────────────────────────────


@router.get(
    "/run",
    summary="Full pipeline result for a host / service",
)
def run_pipeline(
    host: Optional[str] = Query(default=None, description="Host alias"),
    service: Optional[str] = Query(default=None, description="Service name"),
):
    cache = _ensure_cache(host, service)
    target_col = cache["data"]["target_col"]
    pred_col = f"{target_col}_pred"
    metrics = cache["metrics"]
    days_ahead = cache["days_ahead"]

    forecast_df = cache["forecast_df"].copy()
    forecast_df["date"] = pd.to_datetime(forecast_df["timestamp"]).dt.date
    daily = (
        forecast_df.groupby("date")[pred_col].agg(["mean", "min", "max"]).reset_index()
    )

    return {
        "host": host,
        "service": service,
        "target_col": target_col,
        "cached_at": model_cache.get_cached_at(host, service),
        "metrics": metrics,
        "forecast_summary": {
            "days_ahead": days_ahead,
            "forecast_start": str(forecast_df["timestamp"].min()),
            "forecast_end": str(forecast_df["timestamp"].max()),
            "predicted_min": round(float(forecast_df[pred_col].min()), 4),
            "predicted_max": round(float(forecast_df[pred_col].max()), 4),
            "predicted_mean": round(float(forecast_df[pred_col].mean()), 4),
        },
        "daily_averages": [
            {
                "date": str(row["date"]),
                "avg_value": round(float(row["mean"]), 4),
                "min_value": round(float(row["min"]), 4),
                "max_value": round(float(row["max"]), 4),
            }
            for _, row in daily.iterrows()
        ],
    }


# ── GET /predict/combined ─────────────────────────────────────────────────────


@router.get(
    "/combined",
    response_model=CombinedSeriesResponse,
    summary="Historical + forecast combined (main dashboard chart)",
)
def get_combined(
    host: Optional[str] = Query(default=None, description="Host alias"),
    service: Optional[str] = Query(default=None, description="Service name"),
    days: int = Query(default=7, ge=1, le=30, description="Forecast days ahead"),
    granularity: GranularityT = Query(
        default="hourly", description="5min | hourly | 6hour | daily"
    ),
):
    cache = _ensure_cache(host, service)
    forecast_df, days_ahead = _get_forecast_df(cache, host, service, days)

    data = cache["data"]
    target_col = data["target_col"]
    df_full = data["df_full"]
    df_model = data["df_model"]
    pred_col = f"{target_col}_pred"
    rule = RESAMPLE_RULE[granularity]
    ts_fmt = TS_FORMAT[granularity]

    # ── historical: average across hosts then resample ──
    hist = df_full[["check_time"]].copy()
    hist[target_col] = df_model[target_col].reindex(df_full.index).values
    hist = hist.dropna(subset=[target_col])
    hist = hist.set_index("check_time")[target_col].resample(rule).mean().dropna()

    # ── forecast: resample ──
    fcast = forecast_df.copy()
    fcast["timestamp"] = pd.to_datetime(fcast["timestamp"])
    fcast = fcast.set_index("timestamp")[pred_col].resample(rule).mean().dropna()

    decimals = 2 if granularity == "5min" else 1 if granularity == "hourly" else 0

    return CombinedSeriesResponse(
        host=host,
        service=service,
        target_col=target_col,
        granularity=granularity,
        days_ahead=days_ahead,
        forecast_start=str(forecast_df["timestamp"].min()),
        cached_at=model_cache.get_cached_at(host, service),
        historical=[
            SeriesPoint(timestamp=ts.strftime(ts_fmt), value=round(float(v), decimals))
            for ts, v in hist.items()
        ],
        forecast=[
            SeriesPoint(timestamp=ts.strftime(ts_fmt), value=round(float(v), decimals))
            for ts, v in fcast.items()
        ],
    )
