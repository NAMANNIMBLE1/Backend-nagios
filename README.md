# LCP-DX Cooling Capacity Prediction API

REST API for Nagios-based cooling capacity forecasting using Machine Learning.

## Base URL

```
http://<host>:5000
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# fill in your DB credentials

# Run
uvicorn app.app:app --reload --host 0.0.0.0 --port 5000
```

## Environment Variables

| Variable        | Description                        | Example         |
|-----------------|------------------------------------|-----------------|
| `DB_HOST`       | MySQL host                         | `10.10.10.245`  |
| `DB_USER`       | MySQL user                         | `root`          |
| `DB_PASSWORD`   | MySQL password                     | `Root@123`      |
| `DB_NAME`       | MySQL database name                | `nagiosdata`    |
| `FORECAST_DAYS` | Default forecast horizon (days)    | `7`             |
| `RETRAIN_HOUR`  | UTC hour to retrain daily          | `2`             |
| `RETRAIN_MINUTE`| UTC minute to retrain daily        | `0`             |

---

## How It Works

- On startup the model trains automatically and stores everything in memory (cache).
- All prediction/data endpoints read from cache — **no DB hit per request**.
- The model retrains once a day at the configured UTC time.
- `/data/raw` and `/health/` are the only endpoints that hit the DB live.

---

## Endpoints

### Health

#### `GET /health/`

Live system status.

**Response**
```json
{
  "status": "ok",
  "timestamp": "2026-04-01T10:00:00+00:00",
  "db_connected": true,
  "model_ready": true,
  "data_rows": 956,
  "data_start": "2026-03-01 00:00:00",
  "data_end": "2026-03-31 23:55:00",
  "last_trained_at": "2026-04-01T02:00:00",
  "next_retrain_at": "2026-04-02T02:00:00+00:00"
}
```

| Field            | Type    | Description                                 |
|------------------|---------|---------------------------------------------|
| `status`         | string  | `"ok"` or `"degraded"`                      |
| `db_connected`   | boolean | Whether DB is reachable right now            |
| `model_ready`    | boolean | Whether model has been trained and cached    |
| `data_rows`      | int     | Number of rows fetched from DB               |
| `last_trained_at`| string  | ISO timestamp of last training run           |
| `next_retrain_at`| string  | ISO timestamp of next scheduled retrain      |

---

### Data

#### `GET /data/raw?limit=1000`

Raw rows directly from the database. Useful for debugging.

**Query params**

| Param   | Type | Default | Range    |
|---------|------|---------|----------|
| `limit` | int  | `1000`  | 1 – 5000 |

**Response**
```json
{
  "total_rows": 956,
  "columns": ["host_name", "service_name", "check_time", "check_state",
               "state_type", "check_output", "perf_data", "execution_time", "return_code"],
  "data": [
    {
      "host_name": "DL-LCP-DX-01",
      "service_name": "LCP-DX_Cooling-Capacity",
      "check_time": "2026-03-01 00:00:00",
      "check_state": 0,
      "perf_data": "LCP-DX_Cooling-Capacity=35%;90;95;0;100"
    }
  ]
}
```

---

#### `GET /data/stats`

Statistics for the target metric from the cached training data.

**Response**
```json
{
  "target_col": "LCP-DX_Cooling-Capacity",
  "y_min": 35.0,
  "y_max": 35.0,
  "y_mean": 35.0,
  "y_std": 0.0,
  "total_rows": 921,
  "date_range_start": "2026-03-01 00:00:00",
  "date_range_end": "2026-03-31 23:55:00",
  "check_frequency_minutes": 5,
  "hosts": ["DL-LCP-DX-01", "DL-LCP-DX-02", "DL-LCP-DX-03", "DL-LCP-DX-04"]
}
```

---

#### `GET /data/processed`

Feature matrix shape and sample. Useful for understanding what the model trained on.

**Response**
```json
{
  "total_rows": 921,
  "target_col": "LCP-DX_Cooling-Capacity",
  "metric_cols": ["LCP-DX_Cooling-Capacity"],
  "feature_names": ["time_index", "hour", "minute", "day_of_week", "day_of_month",
                    "is_weekend", "is_warning", "is_critical",
                    "LCP-DX_Cooling-Capacity_lag1", "LCP-DX_Cooling-Capacity_lag3",
                    "LCP-DX_Cooling-Capacity_lag6", "LCP-DX_Cooling-Capacity_lag12",
                    "LCP-DX_Cooling-Capacity_roll_mean_12", "LCP-DX_Cooling-Capacity_roll_std_12",
                    "LCP-DX_Cooling-Capacity_roll_mean_36", "LCP-DX_Cooling-Capacity_roll_max_12"],
  "X_shape": [921, 16],
  "y_shape": [921],
  "X_sample": [[0.0, 0, 0, 0, 1, 0, 0, 0, 35.0, 35.0, 35.0, 35.0, 35.0, 0.0, 35.0, 35.0]],
  "y_sample": [35.0, 35.0, 35.0, 35.0, 35.0]
}
```

---

#### `GET /data/timeseries?host=DL-LCP-DX-01`

Full historical timeseries for charting. Optionally filter by host.

**Query params**

| Param  | Type   | Default | Description                     |
|--------|--------|---------|---------------------------------|
| `host` | string | `null`  | Filter to a single host (optional) |

**Response**
```json
{
  "target_col": "LCP-DX_Cooling-Capacity",
  "total_points": 921,
  "cached_at": "2026-04-01T02:00:00",
  "series": [
    { "timestamp": "2026-03-01 00:00:00", "value": 35.0 },
    { "timestamp": "2026-03-01 00:05:00", "value": 35.0 }
  ]
}
```

---

### Prediction

#### `GET /predict/metrics`

Model evaluation metrics computed on the held-out 20% test set.

**Response**
```json
{
  "target_col": "LCP-DX_Cooling-Capacity",
  "mae": 0.0,
  "rmse": 0.0,
  "r2": 1.0,
  "train_rows": 736,
  "test_rows": 185
}
```

| Field       | Description                                |
|-------------|--------------------------------------------|
| `mae`       | Mean Absolute Error (lower = better)       |
| `rmse`      | Root Mean Squared Error (lower = better)   |
| `r2`        | R² score (1.0 = perfect fit)               |
| `train_rows`| Rows used for training (80% split)         |
| `test_rows` | Rows used for evaluation (20% split)       |

---

#### `GET /predict/combined?days=7&granularity=hourly`

**Main endpoint for charting.** Returns historical actuals + future forecast in one response, resampled to the requested granularity.

**Query params**

| Param         | Type   | Default   | Options                          |
|---------------|--------|-----------|----------------------------------|
| `days`        | int    | `7`       | 1 – 30                           |
| `granularity` | string | `"hourly"`| `5min`, `hourly`, `6hour`, `daily` |

**Granularity explained**

| Value    | Bucket size | Points per day | Decimal places |
|----------|-------------|----------------|----------------|
| `5min`   | 5 minutes   | 288            | 2              |
| `hourly` | 1 hour      | 24             | 1              |
| `6hour`  | 6 hours     | 4              | 0              |
| `daily`  | 1 day       | 1              | 0              |

**Response**
```json
{
  "target_col": "LCP-DX_Cooling-Capacity",
  "granularity": "hourly",
  "days_ahead": 7,
  "forecast_start": "2026-04-01 00:00:00",
  "cached_at": "2026-04-01T02:00:00",
  "historical": [
    { "timestamp": "01 Mar 00:00", "value": 35.0 },
    { "timestamp": "01 Mar 01:00", "value": 35.0 }
  ],
  "forecast": [
    { "timestamp": "01 Apr 00:00", "value": 35.0 },
    { "timestamp": "01 Apr 01:00", "value": 35.0 }
  ]
}
```

> **Tip**: Use `historical` for the left side of the chart, `forecast` for the right. Draw a vertical reference line at `forecast_start`.

---

#### `GET /predict/summary?days=7`

Daily aggregated forecast — lighter payload for dashboards and tables.

**Query params**

| Param  | Type | Default | Range  |
|--------|------|---------|--------|
| `days` | int  | `7`     | 1 – 30 |

**Response**
```json
{
  "target_col": "LCP-DX_Cooling-Capacity",
  "days_ahead": 7,
  "forecast_start": "2026-04-01 00:00:00",
  "forecast_end": "2026-04-07 23:55:00",
  "predicted_min": 35.0,
  "predicted_max": 35.0,
  "predicted_mean": 35.0,
  "daily_averages": [
    { "date": "2026-04-01", "avg_value": 35.0, "min_value": 35.0, "max_value": 35.0 },
    { "date": "2026-04-02", "avg_value": 35.0, "min_value": 35.0, "max_value": 35.0 }
  ]
}
```

---

#### `GET /predict/forecast?days=7`

Every 5-minute predicted value for the next N days. **Large payload** — use `/predict/summary` or `/predict/combined` for dashboards.

**Query params**

| Param  | Type | Default | Range  |
|--------|------|---------|--------|
| `days` | int  | `7`     | 1 – 30 |

**Response**
```json
{
  "target_col": "LCP-DX_Cooling-Capacity",
  "days_ahead": 7,
  "total_steps": 2016,
  "forecast_start": "2026-04-01 00:00:00",
  "forecast_end": "2026-04-07 23:55:00",
  "predicted_min": 35.0,
  "predicted_max": 35.0,
  "predicted_mean": 35.0,
  "forecast": [
    { "timestamp": "2026-04-01 00:05:00", "predicted_value": 35.0 },
    { "timestamp": "2026-04-01 00:10:00", "predicted_value": 35.0 }
  ]
}
```

---

#### `GET /predict/actual-vs-predicted`

Actual and predicted pairs from the test split. Use for accuracy charts.

**Response**
```json
{
  "target_col": "LCP-DX_Cooling-Capacity",
  "total_points": 185,
  "cached_at": "2026-04-01T02:00:00",
  "series": [
    { "index": 0, "actual": 35.0, "predicted": 35.0 },
    { "index": 1, "actual": 35.0, "predicted": 35.0 }
  ]
}
```

---

#### `GET /predict/run`

Full pipeline result from cache — metrics + forecast summary in one response.

**Response**
```json
{
  "target_col": "LCP-DX_Cooling-Capacity",
  "cached_at": "2026-04-01T02:00:00",
  "metrics": {
    "mae": 0.0,
    "rmse": 0.0,
    "r2": 1.0,
    "train_rows": 736,
    "test_rows": 185
  },
  "forecast_summary": {
    "days_ahead": 7,
    "forecast_start": "2026-04-01 00:00:00",
    "forecast_end": "2026-04-07 23:55:00",
    "predicted_min": 35.0,
    "predicted_max": 35.0,
    "predicted_mean": 35.0
  },
  "daily_averages": [
    { "date": "2026-04-01", "avg_value": 35.0, "min_value": 35.0, "max_value": 35.0 }
  ]
}
```

---

#### `GET /routes/`

All registered API routes grouped by tag.

**Response**
```json
{
  "total": 11,
  "routes": {
    "Health": [
      { "method": "GET", "path": "/health/", "name": "health_check", "summary": "System health check" }
    ],
    "Prediction": [
      { "method": "GET", "path": "/predict/combined", "name": "get_combined", "summary": "Historical + forecast combined" }
    ]
  }
}
```

---

## Error Responses

All endpoints return standard HTTP errors:

| Status | When                                               |
|--------|----------------------------------------------------|
| `200`  | Success                                            |
| `500`  | Internal server error (check logs)                 |
| `503`  | Model not ready — training still running on startup|

**503 response body:**
```json
{
  "detail": "Model not ready — training is still running. Retry in a moment."
}
```

> On first startup, training takes 10–30 seconds. Poll `/health/` until `model_ready: true` before hitting prediction endpoints.

---

## Recommended Endpoint Usage

| Use case                  | Endpoint                                    |
|---------------------------|---------------------------------------------|
| Main chart (hist+forecast)| `GET /predict/combined?days=7&granularity=hourly` |
| Daily forecast table      | `GET /predict/summary?days=7`               |
| Model quality badges      | `GET /predict/metrics`                      |
| System status bar         | `GET /health/`                              |
| Data info strip           | `GET /data/stats`                           |
| Debug raw data            | `GET /data/raw`                             |

---

## Interactive Docs

| URL           | Description       |
|---------------|-------------------|
| `/docs`       | Swagger UI        |
| `/redoc`      | ReDoc             |
| `/routes/`    | JSON route list   |