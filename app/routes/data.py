from fastapi import APIRouter, HTTPException, Query
import numpy as np
import pandas as pd

from app.cache import model_cache
from db.db_connection import get_sql_data
from app.schemas.response import (
    RawDataResponse,
    ProcessedDataResponse,
    FeatureStatsResponse,
)

router = APIRouter(prefix="/data", tags=["Data"])


def _require_cache() -> dict:
    if not model_cache.is_ready():
        raise HTTPException(
            status_code=503,
            detail="Model not ready — training is still running. Retry in a moment.",
        )
    return model_cache.get_cache()


# GET /data/raw

@router.get("/raw", response_model=RawDataResponse, summary="Raw rows from database")
def get_raw_data(
    limit: int = Query(default=1000, ge=1, le=5000, description="Number of rows to return")
):
    try:
        result  = get_sql_data()
        rows    = result["rows"]
        columns = result["columns"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")

    records = []
    for row in rows[:limit]:
        record = {}
        for col, val in zip(columns, row):
            record[col] = str(val) if not isinstance(val, (int, float, str, type(None))) else val
        records.append(record)

    return RawDataResponse(total_rows=len(rows), columns=columns, data=records)


# GET /data/processed

@router.get("/processed", response_model=ProcessedDataResponse, summary="Processed X / y arrays")
def get_processed_data():
    cache = _require_cache()
    data  = cache["data"]
    X, y  = data["X"], data["y"]

    return ProcessedDataResponse(
        total_rows    = len(X),
        target_col    = data["target_col"],
        metric_cols   = data["metric_cols"],
        feature_names = data["feature_names"],
        X_shape       = list(X.shape),
        y_shape       = list(y.shape),
        X_sample      = X[:5].tolist(),
        y_sample      = y[:5].tolist(),
    )


# GET /data/stats

@router.get("/stats", response_model=FeatureStatsResponse, summary="Target metric statistics")
def get_feature_stats():
    cache      = _require_cache()
    data       = cache["data"]
    df_full    = data["df_full"]
    target_col = data["target_col"]
    y          = data["y"]

    # ── Fix: compute per-host to avoid zero diffs from interleaved multi-host rows ──
    freq = 5  # safe fallback
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


# GET /data/timeseries

@router.get("/timeseries", summary="Full historical timeseries for charting")
def get_timeseries(
    host: str = Query(default=None, description="Filter by host name")
):
    cache      = _require_cache()
    data       = cache["data"]
    df_full    = data["df_full"]
    target_col = data["target_col"]
    df_model   = data["df_model"]

    df = df_full[["check_time", "host_name"]].copy()
    df[target_col] = df_model[target_col].reindex(df_full.index).values

    if host and "host_name" in df_full.columns:
        df = df[df["host_name"] == host]

    df = df.dropna(subset=[target_col])

    return {
        "target_col"  : target_col,
        "total_points": len(df),
        "cached_at"   : model_cache.get_cached_at(),
        "series"      : [
            {"timestamp": str(row["check_time"]), "value": round(float(row[target_col]), 4)}
            for _, row in df.iterrows()
        ],
    }