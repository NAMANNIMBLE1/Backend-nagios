"""
data_processing.py
~~~~~~~~~~~~~~~~~~
Feature engineering and dataset preparation.

Main entry point: prediction_tabular_data(host, service, days)
"""

import re
import logging
from typing import Optional

import numpy as np
import pandas as pd

from db.db_connection import get_sql_data

logger = logging.getLogger(__name__)


# ── perfdata parser ───────────────────────────────────────────────────────────

def parse_perfdata(perfdata_str: str) -> dict:
    """
    Parse Nagios perfdata string → dict of numeric values.

    Example:
        'power=1240W;1500;1800;0;2000 cooling_capacity=85%;90;95;0;100'
        → {'power': 1240.0, 'cooling_capacity': 85.0}
    """
    result: dict = {}
    if not perfdata_str or pd.isna(perfdata_str):
        return result

    for key, val in re.findall(r"([\w\-]+)=([\d.]+)", str(perfdata_str)):
        try:
            result[key] = float(val)
        except ValueError:
            pass
    return result


# ── feature builder ───────────────────────────────────────────────────────────

def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Enrich raw rows with:
      - parsed perfdata columns
      - temporal features
      - lag / rolling features per metric
      - warning / critical state flags
    """
    df = df.copy()
    df["check_time"] = pd.to_datetime(df["check_time"])
    df = df.sort_values("check_time").reset_index(drop=True)

    # ── perfdata → numeric columns ──
    parsed  = df["perf_data"].apply(parse_perfdata)
    perf_df = pd.json_normalize(parsed)
    df      = pd.concat([df, perf_df], axis=1)

    metric_cols = perf_df.columns.tolist()
    logger.info("[FE] Parsed perfdata columns: %s", metric_cols)

    # ── temporal features ──
    df["hour"]         = df["check_time"].dt.hour
    df["minute"]       = df["check_time"].dt.minute
    df["day_of_week"]  = df["check_time"].dt.dayofweek
    df["day_of_month"] = df["check_time"].dt.day
    df["is_weekend"]   = (df["day_of_week"] >= 5).astype(int)

    df["time_index"] = (
        df["check_time"] - df["check_time"].min()
    ).dt.total_seconds() / 3600   # hours since first check

    # ── lag + rolling per metric ──
    for col in metric_cols:
        df[f"{col}_lag1"]         = df[col].shift(1)
        df[f"{col}_lag3"]         = df[col].shift(3)
        df[f"{col}_lag6"]         = df[col].shift(6)
        df[f"{col}_lag12"]        = df[col].shift(12)
        df[f"{col}_roll_mean_12"] = df[col].rolling(12).mean()
        df[f"{col}_roll_std_12"]  = df[col].rolling(12).std()
        df[f"{col}_roll_mean_36"] = df[col].rolling(36).mean()
        df[f"{col}_roll_max_12"]  = df[col].rolling(12).max()

    # ── state flags ──
    df["is_warning"]  = (df["check_state"] == 1).astype(int)
    df["is_critical"] = (df["check_state"] == 2).astype(int)

    return df, metric_cols


# ── regression dataset builder ────────────────────────────────────────────────

def prepare_regression_data(
    df: pd.DataFrame,
    target_col: str,
) -> tuple[np.ndarray, np.ndarray, list[str], pd.DataFrame]:
    """
    Build X / y arrays from a feature-enriched DataFrame.

    Returns (X, y, feature_names, df_model)
    """
    feature_cols = [
        "time_index",
        "hour", "minute", "day_of_week", "day_of_month", "is_weekend",
        "is_warning", "is_critical",
        f"{target_col}_lag1",
        f"{target_col}_lag3",
        f"{target_col}_lag6",
        f"{target_col}_lag12",
        f"{target_col}_roll_mean_12",
        f"{target_col}_roll_std_12",
        f"{target_col}_roll_mean_36",
        f"{target_col}_roll_max_12",
    ]
    feature_cols = [c for c in feature_cols if c in df.columns]

    df_model = df[feature_cols + [target_col]].dropna()
    X        = df_model[feature_cols].values
    y        = df_model[target_col].values

    logger.info("[FE] Target: %s | features: %d | rows: %d (dropped %d NaN)",
                target_col, len(feature_cols), len(X), len(df) - len(X))
    logger.info("[FE] y range: %.2f → %.2f", y.min(), y.max())

    return X, y, feature_cols, df_model


# ── main entry point ──────────────────────────────────────────────────────────

def prediction_tabular_data(
    host:    Optional[str] = None,
    service: Optional[str] = None,
    days:    int           = 30,
) -> dict:
    """
    Load raw data from DB for the given (host, service) pair,
    build features, and return everything needed for training.

    Parameters
    ----------
    host    : host alias to filter on  (None → all hosts)
    service : service display_name     (None → all services, first metric used)
    days    : days of history to load  (default 30)

    Returns
    -------
    {
        "X", "y", "feature_names", "df_model", "df_full",
        "target_col", "metric_cols",
        "host", "service",
    }
    """
    raw = get_sql_data(host=host, service=service, days=days)
    if not raw["rows"]:
        raise ValueError(
            f"No data found for host={host!r}, service={service!r}. "
            "Check the names match exactly what is stored in nagios_hosts / nagios_services."
        )

    df_raw = pd.DataFrame(raw["rows"], columns=raw["columns"])
    logger.info("[DP] Raw rows: %d | host=%s | service=%s", len(df_raw), host, service)

    df_feat, metric_cols = build_features(df_raw)

    if not metric_cols:
        raise ValueError(
            f"No numeric metrics parsed from perfdata for host={host!r}, "
            f"service={service!r}. Check perfdata format."
        )

    # When a specific service is requested its first perfdata metric is the target.
    # Otherwise fall back to the first metric found globally.
    target_col = metric_cols[0]
    logger.info("[DP] Auto-selected target: %s", target_col)

    X, y, feature_names, df_model = prepare_regression_data(df_feat, target_col)

    return {
        "X":            X,
        "y":            y,
        "feature_names": feature_names,
        "df_model":     df_model,
        "df_full":      df_feat,
        "target_col":   target_col,
        "metric_cols":  metric_cols,
        "host":         host,
        "service":      service,
    }


if __name__ == "__main__":
    result = prediction_tabular_data(host="DL-LCP-DX-01", service="LCP-DX_Cooling-Capacity")
    print(f"X shape: {result['X'].shape}")
    print(f"y shape: {result['y'].shape}")
    print(f"Target : {result['target_col']}")
