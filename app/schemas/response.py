from pydantic import BaseModel
from typing import Any, Optional

# HEALTH

class HealthResponse(BaseModel):
    status: str                   # "ok" | "degraded"
    timestamp: str
    db_connected: bool
    model_ready: bool
    data_rows: int
    data_start: Optional[str] = None
    data_end: Optional[str]   = None



# DATA

class RawDataResponse(BaseModel):
    total_rows: int
    columns: list[str]
    data: list[dict]


class ProcessedDataResponse(BaseModel):
    total_rows: int
    target_col: str
    metric_cols: list[str]
    feature_names: list[str]
    X_shape: list[int]
    y_shape: list[int]
    X_sample: list[list[float]]
    y_sample: list[float]


class FeatureStatsResponse(BaseModel):
    target_col: str
    y_min: float
    y_max: float
    y_mean: float
    y_std: float
    total_rows: int
    date_range_start: str
    date_range_end: str
    check_frequency_minutes: int
    hosts: list[str]



# PREDICTION

class ModelMetricsResponse(BaseModel):
    target_col: str
    mae: float
    rmse: float
    r2: float
    train_rows: int
    test_rows: int


class ForecastPoint(BaseModel):
    timestamp: str
    predicted_value: float


class ForecastResponse(BaseModel):
    target_col: str
    days_ahead: int
    total_steps: int
    forecast_start: str
    forecast_end: str
    predicted_min: float
    predicted_max: float
    predicted_mean: float
    forecast: list[ForecastPoint]


class DailyAverage(BaseModel):
    date: str
    avg_value: float
    min_value: float
    max_value: float


class ForecastSummaryResponse(BaseModel):
    target_col: str
    days_ahead: int
    forecast_start: str
    forecast_end: str
    predicted_min: float
    predicted_max: float
    predicted_mean: float
    daily_averages: list[DailyAverage]