"""
routes/data.py
~~~~~~~~~~~~~~
All data-inspection endpoints.

All routes now accept ?host= and ?service= query parameters.
If a model is not yet cached for the requested (host, service) pair, training
is triggered automatically before the response is returned.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.cache.model_cache import model_cache
from app.schemas.response import (
    RawDataResponse,
    ProcessedDataResponse,
    FeatureStatsResponse,
)

import time
from db.db_connection import get_sql_data

# Simple in-memory cache for /data/raw endpoint
_raw_data_cache = {"data": None, "timestamp": 0, "params": None}
_RAW_DATA_TTL = 300  # seconds (5 minutes)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/data", tags=["Data"])


# ── shared helpers ────────────────────────────────────────────────────────────

def _ensure_cache(host: Optional[str], service: Optional[str]) -> dict:
    """Return the cache entry for (host, service), training first if needed."""
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


# ── GET /data/raw ─────────────────────────────────────────────────────────────

@router.get(
    "/raw",
    response_model = RawDataResponse,
    summary        = "Raw rows from database for a host / service",
)
def get_raw_data(
    host:    Optional[str] = Query(default=None, description="Host alias (exact match)"),
    service: Optional[str] = Query(default=None, description="Service display_name (exact match)"),
    limit:   int           = Query(default=1000, ge=1, le=5000, description="Max rows to return"),
    days:    int           = Query(default=30, ge=1, le=365, description="Days of history"),
):
    now = time.time()
    cache_key = (host, service, days, limit)
    if (
        _raw_data_cache["data"] is not None and
        _raw_data_cache["params"] == cache_key and
        now - _raw_data_cache["timestamp"] < _RAW_DATA_TTL
    ):
        result = _raw_data_cache["data"]
        rows    = result["rows"]
        columns = result["columns"]
    else:
        try:
            result  = get_sql_data(host=host, service=service, days=days)
            rows    = result["rows"]
            columns = result["columns"]
            _raw_data_cache["data"] = result
            _raw_data_cache["timestamp"] = now
            _raw_data_cache["params"] = cache_key
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"DB error: {exc}")

    records = []
    for row in rows[:limit]:
        record = {}
        for col, val in zip(columns, row):
            record[col] = str(val) if not isinstance(val, (int, float, str, type(None))) else val
        records.append(record)

    return RawDataResponse(
        host       = host,
        service    = service,
        total_rows = len(rows),
        columns    = columns,
        data       = records,
    )


# ── GET /data/processed ───────────────────────────────────────────────────────

@router.get(
    "/processed",
    response_model = ProcessedDataResponse,
    summary        = "Processed X / y arrays for a host / service",
)
def get_processed_data(
    host:    Optional[str] = Query(default=None, description="Host alias"),
    service: Optional[str] = Query(default=None, description="Service name"),
):
    cache = _ensure_cache(host, service)
    data  = cache["data"]
    X, y  = data["X"], data["y"]

    return ProcessedDataResponse(
        host          = host,
        service       = service,
        total_rows    = len(X),
        target_col    = data["target_col"],
        metric_cols   = data["metric_cols"],
        feature_names = data["feature_names"],
        X_shape       = list(X.shape),
        y_shape       = list(y.shape),
        X_sample      = X[:5].tolist(),
        y_sample      = y[:5].tolist(),
    )


# ── GET /data/stats ───────────────────────────────────────────────────────────

@router.get(
    "/stats",
    response_model = FeatureStatsResponse,
    summary        = "Target metric statistics for a host / service",
)
def get_feature_stats(
    host:    Optional[str] = Query(default=None, description="Host alias"),
    service: Optional[str] = Query(default=None, description="Service name"),
):
    cache      = _ensure_cache(host, service)
    data       = cache["data"]
    df_full    = data["df_full"]
    target_col = data["target_col"]
    y          = data["y"]

    # ── compute check frequency per-host to avoid interleaved-row artefacts ──
    freq = 5
    if "host_name" in df_full.columns:
        per_host = (
            df_full.groupby("host_name")["check_time"]
            .apply(lambda s: s.sort_values().diff().median())
            .dropna()
        )
        if not per_host.empty:
            freq = max(1, int(per_host.median().total_seconds() / 60))
    else:
        td = df_full["check_time"].sort_values().diff().median()
        if pd.notna(td):
            freq = max(1, int(td.total_seconds() / 60))

    hosts = df_full["host_name"].unique().tolist() if "host_name" in df_full.columns else []

    return FeatureStatsResponse(
        host                    = host,
        service                 = service,
        target_col              = target_col,
        y_min                   = float(np.min(y)),
        y_max                   = float(np.max(y)),
        y_mean                  = float(np.mean(y)),
        y_std                   = float(np.std(y)),
        total_rows              = len(y),
        date_range_start        = str(df_full["check_time"].min()),
        date_range_end          = str(df_full["check_time"].max()),
        check_frequency_minutes = freq,
        hosts                   = hosts,
    )


# ── GET /data/timeseries ──────────────────────────────────────────────────────

@router.get(
    "/timeseries",
    summary = "Full historical timeseries for a host / service",
)
def get_timeseries(
    host:        Optional[str] = Query(default=None, description="Host alias"),
    service:     Optional[str] = Query(default=None, description="Service name"),
    filter_host: Optional[str] = Query(default=None, description="Sub-filter: show only one host from multi-host result"),
):
    cache      = _ensure_cache(host, service)
    data       = cache["data"]
    df_full    = data["df_full"]
    target_col = data["target_col"]
    df_model   = data["df_model"]

    df = df_full[["check_time", "host_name"]].copy()
    df[target_col] = df_model[target_col].reindex(df_full.index).values

    if filter_host and "host_name" in df_full.columns:
        df = df[df["host_name"] == filter_host]

    df = df.dropna(subset=[target_col])

    return {
        "host":         host,
        "service":      service,
        "target_col":   target_col,
        "total_points": len(df),
        "cached_at":    model_cache.get_cached_at(host, service),
        "series": [
            {
                "timestamp": str(row["check_time"]),
                "value":     round(float(row[target_col]), 4),
            }
            for _, row in df.iterrows()
        ],
    }
