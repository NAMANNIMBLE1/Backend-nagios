from fastapi import APIRouter, HTTPException, Query
import numpy as np
import pandas as pd

from app.controllers.data_processing import prediction_tabular_data
from db.db_connection import get_sql_data
from app.schemas.response import (
    RawDataResponse,
    ProcessedDataResponse,
    FeatureStatsResponse,
)

router = APIRouter(prefix="/data", tags=["Data"])



# GET /data/raw
# Returns raw DB rows with unparsed perfdata

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
            # serialize datetime → string
            record[col] = str(val) if not isinstance(val, (int, float, str, type(None))) else val
        records.append(record)

    return RawDataResponse(
        total_rows = len(rows),
        columns    = columns,
        data       = records,
    )



@router.get("/processed", response_model=ProcessedDataResponse, summary="Processed X / y arrays")
def get_processed_data():
    try:
        data = prediction_tabular_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

    X             = data["X"]
    y             = data["y"]
    feature_names = data["feature_names"]
    target_col    = data["target_col"]
    metric_cols   = data["metric_cols"]

    return ProcessedDataResponse(
        total_rows    = len(X),
        target_col    = target_col,
        metric_cols   = metric_cols,
        feature_names = feature_names,
        X_shape       = list(X.shape),
        y_shape       = list(y.shape),
        X_sample      = X[:5].tolist(),
        y_sample      = y[:5].tolist(),
    )


@router.get("/stats", response_model=FeatureStatsResponse, summary="Target metric statistics")
def get_feature_stats():
    try:
        data = prediction_tabular_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

    df_full    = data["df_full"]
    target_col = data["target_col"]
    y          = data["y"]

    # Check frequency
    freq = int(
        df_full["check_time"]
        .sort_values()
        .diff()
        .median()
        .total_seconds() / 60
    )

    hosts = (
        df_full["host_name"].unique().tolist()
        if "host_name" in df_full.columns
        else []
    )

    return FeatureStatsResponse(
        target_col             = target_col,
        y_min                  = float(np.min(y)),
        y_max                  = float(np.max(y)),
        y_mean                 = float(np.mean(y)),
        y_std                  = float(np.std(y)),
        total_rows             = len(y),
        date_range_start       = str(df_full["check_time"].min()),
        date_range_end         = str(df_full["check_time"].max()),
        check_frequency_minutes= freq,
        hosts                  = hosts,
    )


@router.get("/timeseries", summary="Full historical timeseries for charting")
def get_timeseries(
    host: str = Query(default=None, description="Filter by host name")
):
    try:
        data = prediction_tabular_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

    df_full    = data["df_full"]
    target_col = data["target_col"]
    df_model   = data["df_model"]

    # Merge check_time back into df_model
    df = df_full[["check_time"]].copy()
    df[target_col] = df_model[target_col].reindex(df_full.index).values

    if host and "host_name" in df_full.columns:
        mask = df_full["host_name"] == host
        df   = df[mask]

    df = df.dropna(subset=[target_col])

    return {
        "target_col": target_col,
        "total_points": len(df),
        "series": [
            {
                "timestamp": str(row["check_time"]),
                "value": round(float(row[target_col]), 4),
            }
            for _, row in df.iterrows()
        ],
    }