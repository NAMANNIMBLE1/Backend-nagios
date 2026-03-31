import logging
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from app.controllers.data_processing import prediction_tabular_data
from app.controllers.predict import train, forecast
from app.cache import model_cache
from config.get_config import get_config

logger = logging.getLogger(__name__)


def run_training_pipeline() -> None:
    config     = get_config()
    days_ahead = int(config.get("FORECAST_DAYS", 7))

    logger.info("[Training] Starting...")

    # 1. Load data and build features
    data = prediction_tabular_data()
    X, y = data["X"], data["y"]

    # 2. Train the model
    model, scaler, y_test, y_pred = train(X, y)

    # 3. Compute metrics once
    split = int(len(X) * 0.8)
    metrics = {
        "mae":        round(float(mean_absolute_error(y_test, y_pred)), 4),
        "rmse":       round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 4),
        "r2":         round(float(r2_score(y_test, y_pred)), 4),
        "train_rows": split,
        "test_rows":  len(X) - split,
    }

    # 4. Generate forecast
    result = forecast(model, scaler, data, days_ahead=days_ahead)
    forecast_df, days_ahead = result if isinstance(result, tuple) else (result, days_ahead)

    # 5. Store everything in cache — this is the only write
    model_cache.set_cache({
        "data":        data,
        "model":       model,
        "scaler":      scaler,
        "y_test":      y_test,
        "y_pred":      y_pred,
        "metrics":     metrics,
        "forecast_df": forecast_df,
        "days_ahead":  days_ahead,
    })

    logger.info("[Training] Done. Cache updated.")