"""
training_service.py
~~~~~~~~~~~~~~~~~~~
Training pipeline callable for a specific (host, service) pair.

Exposed functions
-----------------
run_training_pipeline(host, service)   train + cache one (host, service) entry
retrain_all_cached()                   retrain every currently cached entry (cron job)
"""

import logging
from typing import Optional

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from app.cache.model_cache import model_cache
from app.controllers.data_processing import prediction_tabular_data
from app.controllers.predict import forecast
from config.get_config import get_config

logger = logging.getLogger(__name__)


# ── internal train helper ─────────────────────────────────────────────────────

def _train(X, y):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False   # time-ordered split
    )

    scaler  = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test  = scaler.transform(X_test)

    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    metrics = {
        "mae":        float(mean_absolute_error(y_test, y_pred)),
        "rmse":       float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "r2":         float(r2_score(y_test, y_pred)),
        "train_rows": len(X_train),
        "test_rows":  len(X_test),
    }

    logger.info(
        "[Train] MAE=%.4f  RMSE=%.4f  R²=%.4f  (train=%d / test=%d)",
        metrics["mae"], metrics["rmse"], metrics["r2"],
        metrics["train_rows"], metrics["test_rows"],
    )

    return model, scaler, y_test, y_pred, metrics


# ── public pipeline ───────────────────────────────────────────────────────────

def run_training_pipeline(
    host:    Optional[str] = None,
    service: Optional[str] = None,
    force:   bool          = False,
) -> None:
    """
    Train a model for the given (host, service) pair and store it in the cache.

    If `force=False` and a fresh cache entry already exists, skip training.

    Parameters
    ----------
    host    : Nagios host alias  (None → all hosts)
    service : service name       (None → all services)
    force   : retrain even if cache is warm
    """
    if not force and model_cache.is_ready(host, service):
        logger.info("[Train] Cache warm for host=%s service=%s — skipping", host, service)
        return

    logger.info("[Train] Starting pipeline for host=%s service=%s", host, service)

    config        = get_config()
    days          = int(config.get("HISTORY_DAYS",   30))
    forecast_days = int(config.get("FORECAST_DAYS",   7))

    # ── load + feature engineering ──
    data = prediction_tabular_data(host=host, service=service, days=days)
    X, y = data["X"], data["y"]

    if len(X) < 20:
        raise ValueError(
            f"Not enough data to train for host={host!r}, service={service!r} "
            f"(only {len(X)} usable rows after feature engineering)."
        )

    # ── train ──
    model, scaler, y_test, y_pred, metrics = _train(X, y)

    # ── forecast ──
    forecast_df = forecast(model, scaler, data, days_ahead=forecast_days)

    # ── cache ──
    model_cache.set_cache(
        host        = host,
        service     = service,
        model       = model,
        scaler      = scaler,
        data        = data,
        metrics     = metrics,
        forecast_df = forecast_df,
        days_ahead  = forecast_days,
        y_test      = y_test,
        y_pred      = y_pred,
    )

    logger.info(
        "[Train] Done — host=%s service=%s  target=%s  R²=%.4f",
        host, service, data["target_col"], metrics["r2"],
    )


# ── cron: retrain everything currently in cache ───────────────────────────────

def retrain_all_cached() -> None:
    """
    Called by the APScheduler cron job.
    Retrains every (host, service) pair that is already in the cache.
    """
    keys = model_cache.cached_keys()
    if not keys:
        logger.info("[Retrain] Cache is empty — nothing to retrain")
        return

    logger.info("[Retrain] Retraining %d cached entries", len(keys))
    for entry in keys:
        try:
            run_training_pipeline(
                host    = entry["host"],
                service = entry["service"],
                force   = True,
            )
        except Exception as exc:
            logger.error(
                "[Retrain] Failed for host=%s service=%s: %s",
                entry["host"], entry["service"], exc,
            )
