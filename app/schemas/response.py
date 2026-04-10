from pydantic import BaseModel
from typing import Optional


# ── HEALTH ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status          : str
    timestamp       : str
    db_connected    : bool
    model_ready     : bool          # True if at least one (host,service) is cached
    cached_entries  : int           # how many (host,service) pairs are warm
    data_rows       : int
    data_start      : Optional[str] = None
    data_end        : Optional[str] = None
    last_trained_at : Optional[str] = None
    next_retrain_at : Optional[str] = None


# ── HOSTS / SERVICES ──────────────────────────────────────────────────────────

class HostsResponse(BaseModel):
    total : int
    hosts : list[str]


class ServicesResponse(BaseModel):
    host     : str
    total    : int
    services : list[str]


class CacheEntryInfo(BaseModel):
    host       : Optional[str]
    service    : Optional[str]
    cached_at  : str


class CacheStatusResponse(BaseModel):
    total_cached : int
    entries      : list[CacheEntryInfo]


# ── DATA ──────────────────────────────────────────────────────────────────────

class RawDataResponse(BaseModel):
    host       : Optional[str]
    service    : Optional[str]
    total_rows : int
    columns    : list[str]
    data       : list[dict]


class ProcessedDataResponse(BaseModel):
    host          : Optional[str]
    service       : Optional[str]
    total_rows    : int
    target_col    : str
    metric_cols   : list[str]
    feature_names : list[str]
    X_shape       : list[int]
    y_shape       : list[int]
    X_sample      : list[list[float]]
    y_sample      : list[float]


class FeatureStatsResponse(BaseModel):
    host                    : Optional[str]
    service                 : Optional[str]
    target_col              : str
    y_min                   : float
    y_max                   : float
    y_mean                  : float
    y_std                   : float
    total_rows              : int
    date_range_start        : str
    date_range_end          : str
    check_frequency_minutes : int
    hosts                   : list[str]


# ── PREDICTION ────────────────────────────────────────────────────────────────

class ModelMetricsResponse(BaseModel):
    host       : Optional[str]
    service    : Optional[str]
    target_col : str
    mae        : float
    rmse       : float
    r2         : float
    train_rows : int
    test_rows  : int


class ForecastPoint(BaseModel):
    timestamp       : str
    predicted_value : float


class ForecastResponse(BaseModel):
    host           : Optional[str]
    service        : Optional[str]
    target_col     : str
    days_ahead     : int
    total_steps    : int
    forecast_start : str
    forecast_end   : str
    predicted_min  : float
    predicted_max  : float
    predicted_mean : float
    forecast       : list[ForecastPoint]


class DailyAverage(BaseModel):
    date      : str
    avg_value : float
    min_value : float
    max_value : float


class ForecastSummaryResponse(BaseModel):
    host           : Optional[str]
    service        : Optional[str]
    target_col     : str
    days_ahead     : int
    forecast_start : str
    forecast_end   : str
    predicted_min  : float
    predicted_max  : float
    predicted_mean : float
    daily_averages : list[DailyAverage]


# ── COMBINED (historical + forecast) ──────────────────────────────────────────

class SeriesPoint(BaseModel):
    timestamp : str
    value     : float


class CombinedSeriesResponse(BaseModel):
    host           : Optional[str]
    service        : Optional[str]
    target_col     : str
    granularity    : str
    days_ahead     : int
    forecast_start : str
    cached_at      : Optional[str] = None
    historical     : list[SeriesPoint]
    forecast       : list[SeriesPoint]
