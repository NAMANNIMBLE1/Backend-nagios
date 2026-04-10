# Nagios Service Prediction API

<<<<<<< HEAD
A FastAPI backend that connects to a Nagios-compatible MySQL database, trains a machine learning model per **(host, service)** pair, and serves historical data alongside multi-day forecasts.

---

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Setup & Installation](#setup--installation)
- [Environment Variables](#environment-variables)
- [Running the Server](#running-the-server)
- [API Reference](#api-reference)
  - [Root](#root)
  - [Health](#health)
  - [Hosts & Services Discovery](#hosts--services-discovery)
  - [Data Endpoints](#data-endpoints)
  - [Prediction Endpoints](#prediction-endpoints)
- [Typical Frontend Flow](#typical-frontend-flow)
- [Model Details](#model-details)
- [Caching & Lazy Training](#caching--lazy-training)
- [Scheduled Retraining](#scheduled-retraining)
- [Database Schema Reference](#database-schema-reference)
- [FAQ](#faq)

---
=======
# nagios services usage prediction

REST API for Nagios-based particular host and services forecasting using Machine Learning.
for DCIM data centers


This project is a **web API** that predicts the services usage .
>>>>>>> de8945f6fe55b84f6336e2c85feb76571c75ebdc

## Overview

This backend was built to solve one specific problem:

> A Nagios monitoring system tracks **multiple hosts** (e.g. `DL-LCP-DX-01`, `DL-LCP-DX-02`). Each host has **multiple services** (e.g. `LCP-DX_Power`, `LCP-DX_Cooling-Capacity`, `LCP-DX_Temp-In`). For any combination of host + service, we want to:
> 1. Show **historical check data** (last 30 days)
> 2. Train a **regression model** on that data
> 3. Serve a **multi-day forecast** (default 7 days ahead, up to 30)

The key design principle is **lazy training** — models are trained on the first API request for a `(host, service)` pair and cached in memory. No pre-warming is required at startup.

---

## Project Structure

```
backend/
├── app/
│   ├── app.py                        # FastAPI app, middleware, router registration
│   ├── cache.py                      # Multi-key in-memory model cache
│   ├── scheduler.py                  # APScheduler daily retrain cron job
│   ├── controllers/
│   │   ├── data_processing.py        # Feature engineering, perfdata parsing
│   │   └── predict.py                # Model training + autoregressive forecasting
│   ├── routes/
│   │   ├── health.py                 # GET /health/
│   │   ├── hosts.py                  # GET /hosts/, /hosts/{host}/services, etc.
│   │   ├── data.py                   # GET /data/raw, /processed, /stats, /timeseries
│   │   ├── prediction.py             # GET /predict/forecast, /summary, /combined, etc.
│   │   └── routes.py                 # GET /routes/ (route explorer)
│   ├── schemas/
│   │   └── response.py               # All Pydantic response models
│   └── services/
│       └── training_service.py       # run_training_pipeline(), retrain_all_cached()
├── config/
│   └── get_config.py                 # Loads .env into a dict
├── db/
│   └── db_connection.py              # get_hosts(), get_services_for_host(), get_sql_data()
├── .env                              # Environment variables (not committed)
├── requirements.txt
└── README.md
```

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend / Dashboard                  │
└───────────────────────────┬─────────────────────────────────┘
                            │  HTTP
┌───────────────────────────▼─────────────────────────────────┐
│                        FastAPI Backend                       │
│                                                             │
│  GET /hosts/                                                │
│    └─► db_connection.get_hosts()                            │
│         └─► SELECT DISTINCT h.alias FROM nagios_hosts ...   │
│                                                             │
│  GET /hosts/{host}/services                                 │
│    └─► db_connection.get_services_for_host(host)            │
│         └─► SELECT DISTINCT s.display_name ...              │
│                                                             │
│  GET /predict/combined?host=X&service=Y                     │
│    └─► _ensure_cache(host, service)                         │
│         ├─► [cache miss] run_training_pipeline(host, svc)   │
│         │     ├─► get_sql_data(host, svc, days=30)          │
│         │     ├─► build_features(df)                        │
│         │     ├─► prepare_regression_data(df, target)       │
│         │     ├─► train(X, y)  → LinearRegression           │
│         │     ├─► forecast(model, scaler, data, days=7)     │
│         │     └─► model_cache.set_cache(host, svc, ...)     │
│         └─► [cache hit] return cached model + forecast      │
└─────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                        MySQL Database                        │
│  nagios_hosts → nagios_services → nagios_servicechecks      │
└─────────────────────────────────────────────────────────────┘
```

---

## Setup & Installation

**1. Clone / copy the backend folder**

```bash
cd backend
```

**2. Create a virtual environment**

<<<<<<< HEAD
```bash
python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows
=======
---

## Step 4: Explore the API (No coding needed!)

- Open your browser and go to [http://localhost:5000/docs](http://localhost:5000/docs) for an interactive Swagger UI.
- Or use [http://localhost:5000/redoc](http://localhost:5000/redoc) for a documentation view.

---

## Environment Variables Explained

| Variable        | Description                        | Example         |
|-----------------|------------------------------------|-----------------|
| `DB_HOST`       | MySQL host                         | `10.10.10.1`  |
| `DB_USER`       | MySQL user                         | `sample`          |
| `DB_PASSWORD`   | MySQL password                     | `sample23`      |
| `DB_NAME`       | MySQL database name                | `nagiosdata`    |
| `FORECAST_DAYS` | Default forecast horizon (days)    | `7`             |
| `RETRAIN_HOUR`  | UTC hour to retrain daily          | `2`             |
| `RETRAIN_MINUTE`| UTC minute to retrain daily        | `0`             |

=======
# Install dependencies
install uv package from official site
uv venv
source .venv/bin/activate or for windows .venv/Scripts/activate
uv pip install -r requirements.txt

# Configure environment
cp .env
# fill in your DB credentials
make .env and add db credentials
 
# Run
uvicorn app.app:app --reload --host 0.0.0.0 --port 5000
>>>>>>> de8945f6fe55b84f6336e2c85feb76571c75ebdc
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Create your `.env` file** (see [Environment Variables](#environment-variables))

```bash
cp .env.example .env
# then edit .env with your actual values
```

---

## Environment Variables

Create a `.env` file in the `backend/` root:

```env
# ── Database ──────────────────────────────────────────────
DB_HOST=localhost
DB_PORT=3306
DB_USER=nagios
DB_PASSWORD=your_password_here
DB_NAME=nagios

# ── Training ──────────────────────────────────────────────
HISTORY_DAYS=30          # How many days of history to pull from DB
FORECAST_DAYS=7          # How many days ahead to forecast

# ── Scheduler ─────────────────────────────────────────────
RETRAIN_HOUR=2           # UTC hour for daily retrain cron (0-23)
RETRAIN_MINUTE=0         # UTC minute for daily retrain cron
```

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | — | MySQL server hostname |
| `DB_PORT` | `3306` | MySQL port |
| `DB_USER` | — | MySQL username |
| `DB_PASSWORD` | — | MySQL password |
| `DB_NAME` | — | Database name (usually `nagios`) |
| `HISTORY_DAYS` | `30` | Days of service-check history used for training |
| `FORECAST_DAYS` | `7` | Default forecast horizon in days |
| `RETRAIN_HOUR` | `2` | Hour (UTC) when the daily retrain cron fires |
| `RETRAIN_MINUTE` | `0` | Minute when the daily retrain cron fires |

---

## Running the Server

```bash
# Development (auto-reload)
uvicorn app.app:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.app:app --host 0.0.0.0 --port 8000 --workers 2
```

Once running, open:
- **Swagger UI** → http://localhost:8000/docs
- **ReDoc** → http://localhost:8000/redoc
- **Route explorer** → http://localhost:8000/routes/

---

## API Reference

### Root

#### `GET /`
Returns a summary of all available routes.

```json
{
  "name": "Nagios Service Prediction API",
  "version": "2.0.0",
  "docs": "/docs"
}
```

---

### Health

#### `GET /health/`

Returns the current system status — database connectivity, how many models are cached, and when the next retrain is scheduled.

**Response**
```json
{
  "status": "ok",
  "timestamp": "2026-04-10T08:00:00+00:00",
  "db_connected": true,
  "model_ready": true,
  "cached_entries": 3,
  "data_rows": 8640,
  "data_start": "2026-03-10 00:00:00",
  "data_end": "2026-04-09 23:55:00",
  "last_trained_at": "2026-04-10T02:00:00+00:00",
  "next_retrain_at": "2026-04-11T02:00:00+00:00"
}
```

| Field | Description |
|---|---|
| `status` | `ok` if DB connected AND at least one model cached, otherwise `degraded` |
| `cached_entries` | Number of `(host, service)` pairs with a trained model in memory |
| `model_ready` | `true` if any model is cached |

---

### Hosts & Services Discovery

These are the endpoints your UI uses to populate dropdown menus.

---

#### `GET /hosts/`

Returns all host aliases that have service-check data in the database.

**Response**
```json
{
  "total": 4,
  "hosts": [
    "DL-LCP-DX-01",
    "DL-LCP-DX-02",
    "DL-LCP-DX-03",
    "DL-LCP-DX-04"
  ]
}
```

---

#### `GET /hosts/{host_name}/services`

Returns all service names available for a specific host. Use this to populate the service dropdown after the user selects a host.

**Path parameter:** `host_name` — must match `nagios_hosts.alias` exactly.

**Example:** `GET /hosts/DL-LCP-DX-01/services`

**Response**
```json
{
  "host": "DL-LCP-DX-01",
  "total": 23,
  "services": [
    "LCP-DX_Cooling-Capacity",
    "LCP-DX_Fan-Speed",
    "LCP-DX_Power",
    "LCP-DX_Temp-In",
    "LCP-DX_Temp-Out",
    "LCP-DX_Unit-Voltage"
  ]
}
```

---

#### `GET /hosts/cache`

Shows which `(host, service)` pairs currently have a trained model in memory and when they were last trained.

**Response**
```json
{
  "total_cached": 2,
  "entries": [
    {
      "host": "DL-LCP-DX-01",
      "service": "LCP-DX_Power",
      "cached_at": "2026-04-10T08:12:00+00:00"
    },
    {
      "host": "DL-LCP-DX-02",
      "service": "LCP-DX_Cooling-Capacity",
      "cached_at": "2026-04-10T08:15:00+00:00"
    }
  ]
}
```

---

#### `DELETE /hosts/cache`

Invalidates a cached model so it will be retrained on the next request.

**Query parameters:**
| Param | Required | Description |
|---|---|---|
| `host` | No | Host alias |
| `service` | No | Service name |

**Example:** `DELETE /hosts/cache?host=DL-LCP-DX-01&service=LCP-DX_Power`

**Response**
```json
{
  "invalidated": true,
  "host": "DL-LCP-DX-01",
  "service": "LCP-DX_Power",
  "message": "Cache entry removed. Next API call will trigger retraining."
}
```

---

#### `POST /hosts/{host_name}/services/{service_name}/train`

Manually trigger training for a specific `(host, service)` pair. Useful for pre-warming the cache before users arrive on the dashboard.

**Path parameters:** `host_name`, `service_name`

**Query parameters:**
| Param | Default | Description |
|---|---|---|
| `force` | `false` | Retrain even if a cached model already exists |

**Example:** `POST /hosts/DL-LCP-DX-01/services/LCP-DX_Power/train`

**Response**
```json
{
  "status": "trained",
  "host": "DL-LCP-DX-01",
  "service": "LCP-DX_Power",
  "cached_at": "2026-04-10T08:12:00+00:00",
  "message": "Model trained and cached successfully."
}
```

---

### Data Endpoints

All data endpoints accept `?host=` and `?service=` query parameters. If the model is not yet cached, training is triggered automatically.

---

#### `GET /data/raw`

Returns raw rows directly from the database for inspection.

**Query parameters:**
| Param | Default | Description |
|---|---|---|
| `host` | `null` | Filter by host alias |
| `service` | `null` | Filter by service name |
| `limit` | `1000` | Max rows to return (1–5000) |
| `days` | `30` | Days of history to fetch |

**Example:** `GET /data/raw?host=DL-LCP-DX-01&service=LCP-DX_Power&limit=100`

**Response**
```json
{
  "host": "DL-LCP-DX-01",
  "service": "LCP-DX_Power",
  "total_rows": 8640,
  "columns": ["host_name", "service_name", "check_time", "check_state", "perf_data", "..."],
  "data": [
    {
      "host_name": "DL-LCP-DX-01",
      "service_name": "LCP-DX_Power",
      "check_time": "2026-03-11 00:00:00",
      "check_state": "0",
      "perf_data": "power=1240W;1500;1800;0;2000"
    }
  ]
}
```

---

#### `GET /data/processed`

Returns the feature-engineered X and y arrays used for model training.

**Query parameters:** `host`, `service`

**Response**
```json
{
  "host": "DL-LCP-DX-01",
  "service": "LCP-DX_Power",
  "total_rows": 7800,
  "target_col": "power",
  "metric_cols": ["power"],
  "feature_names": ["time_index", "hour", "minute", "power_lag1", "power_roll_mean_12", "..."],
  "X_shape": [7800, 16],
  "y_shape": [7800],
  "X_sample": [[...], [...], [...], [...], [...]],
  "y_sample": [1240.0, 1245.5, 1238.0, 1252.0, 1260.0]
}
```

---

#### `GET /data/stats`

Returns statistical summary of the target metric for a host/service.

**Query parameters:** `host`, `service`

**Response**
```json
{
  "host": "DL-LCP-DX-01",
  "service": "LCP-DX_Power",
  "target_col": "power",
  "y_min": 980.0,
  "y_max": 1650.0,
  "y_mean": 1243.7,
  "y_std": 89.4,
  "total_rows": 7800,
  "date_range_start": "2026-03-11 00:00:00",
  "date_range_end": "2026-04-09 23:55:00",
  "check_frequency_minutes": 5,
  "hosts": ["DL-LCP-DX-01"]
}
```

---

#### `GET /data/timeseries`

Returns the full historical timeseries for charting.

**Query parameters:**
| Param | Default | Description |
|---|---|---|
| `host` | `null` | Host alias |
| `service` | `null` | Service name |
| `filter_host` | `null` | If multiple hosts loaded, show only this one |

**Response**
```json
{
  "host": "DL-LCP-DX-01",
  "service": "LCP-DX_Power",
  "target_col": "power",
  "total_points": 7800,
  "cached_at": "2026-04-10T08:12:00+00:00",
  "series": [
    { "timestamp": "2026-03-11 00:00:00", "value": 1240.0 },
    { "timestamp": "2026-03-11 00:05:00", "value": 1245.5 }
  ]
}
```

---

### Prediction Endpoints

All prediction endpoints accept `?host=` and `?service=`. Training is triggered automatically on cache miss.

---

#### `GET /predict/metrics`

Returns model evaluation metrics from the last training run.

**Query parameters:** `host`, `service`

**Response**
```json
{
  "host": "DL-LCP-DX-01",
  "service": "LCP-DX_Power",
  "target_col": "power",
  "mae": 12.34,
  "rmse": 18.92,
  "r2": 0.9421,
  "train_rows": 6240,
  "test_rows": 1560
}
```

| Metric | Description |
|---|---|
| `mae` | Mean Absolute Error — average prediction error in original units |
| `rmse` | Root Mean Squared Error — penalises large errors more |
| `r2` | R² score — 1.0 is perfect, 0.0 means no better than the mean |

---

#### `GET /predict/forecast`

Returns the full 5-minute-step forecast for the requested number of days.

**Query parameters:**
| Param | Default | Description |
|---|---|---|
| `host` | `null` | Host alias |
| `service` | `null` | Service name |
| `days` | `7` | Days ahead to forecast (1–30) |

**Example:** `GET /predict/forecast?host=DL-LCP-DX-01&service=LCP-DX_Power&days=7`

**Response**
```json
{
  "host": "DL-LCP-DX-01",
  "service": "LCP-DX_Power",
  "target_col": "power",
  "days_ahead": 7,
  "total_steps": 2016,
  "forecast_start": "2026-04-10 00:05:00",
  "forecast_end": "2026-04-16 23:55:00",
  "predicted_min": 980.0,
  "predicted_max": 1620.0,
  "predicted_mean": 1238.4,
  "forecast": [
    { "timestamp": "2026-04-10 00:05:00", "predicted_value": 1242.5 },
    { "timestamp": "2026-04-10 00:10:00", "predicted_value": 1239.1 }
  ]
}
```

---

#### `GET /predict/summary`

Returns the forecast aggregated by day — min, max, and average per day. Easier to display in a table.

**Query parameters:** `host`, `service`, `days`

**Response**
```json
{
  "host": "DL-LCP-DX-01",
  "service": "LCP-DX_Power",
  "target_col": "power",
  "days_ahead": 7,
  "forecast_start": "2026-04-10 00:05:00",
  "forecast_end": "2026-04-16 23:55:00",
  "predicted_min": 980.0,
  "predicted_max": 1620.0,
  "predicted_mean": 1238.4,
  "daily_averages": [
    { "date": "2026-04-10", "avg_value": 1241.0, "min_value": 1010.0, "max_value": 1580.0 },
    { "date": "2026-04-11", "avg_value": 1235.5, "min_value": 990.0,  "max_value": 1600.0 }
  ]
}
```

---

#### `GET /predict/actual-vs-predicted`

Returns actual vs predicted values on the held-out test set. Useful for evaluating model quality visually.

**Query parameters:** `host`, `service`

**Response**
```json
{
  "host": "DL-LCP-DX-01",
  "service": "LCP-DX_Power",
  "target_col": "power",
  "total_points": 1560,
  "cached_at": "2026-04-10T08:12:00+00:00",
  "series": [
    { "index": 0, "actual": 1240.0, "predicted": 1238.5 },
    { "index": 1, "actual": 1245.0, "predicted": 1243.1 }
  ]
}
```

---

#### `GET /predict/combined` ⭐ Main dashboard endpoint

Returns **historical actuals + future forecast** in a single response, resampled to the requested granularity. This is the primary endpoint for the dashboard chart.

**Query parameters:**
| Param | Default | Options | Description |
|---|---|---|---|
| `host` | `null` | — | Host alias |
| `service` | `null` | — | Service name |
| `days` | `7` | 1–30 | Forecast days ahead |
| `granularity` | `hourly` | `5min`, `hourly`, `6hour`, `daily` | Time bucket size |

**Example:** `GET /predict/combined?host=DL-LCP-DX-01&service=LCP-DX_Power&days=7&granularity=hourly`

**Response**
```json
{
  "host": "DL-LCP-DX-01",
  "service": "LCP-DX_Power",
  "target_col": "power",
  "granularity": "hourly",
  "days_ahead": 7,
  "forecast_start": "2026-04-10 00:05:00",
  "cached_at": "2026-04-10T08:12:00+00:00",
  "historical": [
    { "timestamp": "10 Mar 00:00", "value": 1241.0 },
    { "timestamp": "10 Mar 01:00", "value": 1238.5 }
  ],
  "forecast": [
    { "timestamp": "10 Apr 09:00", "value": 1245.0 },
    { "timestamp": "10 Apr 10:00", "value": 1240.3 }
  ]
}
```

---

#### `GET /predict/run`

Returns a full pipeline result in one response — metrics + forecast summary. Useful for a summary panel.

**Query parameters:** `host`, `service`

---

## Typical Frontend Flow

Here is exactly how a React / Vue dashboard would use this API:

```
1. On page load
   GET /hosts/
   → populate host dropdown

2. User selects "DL-LCP-DX-01"
   GET /hosts/DL-LCP-DX-01/services
   → populate service dropdown

3. User selects "LCP-DX_Power"
   GET /predict/combined?host=DL-LCP-DX-01&service=LCP-DX_Power&granularity=hourly
   → render chart (historical line + forecast dashed line)
   
   GET /predict/metrics?host=DL-LCP-DX-01&service=LCP-DX_Power
   → render MAE / RMSE / R² info card
   
   GET /predict/summary?host=DL-LCP-DX-01&service=LCP-DX_Power&days=7
   → render daily forecast table

4. User changes days to 14
   GET /predict/combined?host=DL-LCP-DX-01&service=LCP-DX_Power&days=14&granularity=daily
   → re-render chart with 14-day forecast

5. User switches to "DL-LCP-DX-02" + "LCP-DX_Cooling-Capacity"
   → repeat from step 3 with new params
   → training fires automatically on first request if not yet cached
```

> **Note on first load:** The very first request for a `(host, service)` pair triggers training synchronously — this may take a few seconds depending on data volume. All subsequent requests for the same pair are instant (served from cache). You can pre-warm pairs using `POST /hosts/{host}/services/{service}/train` on startup.

---

## Model Details

### Algorithm
Linear Regression (from scikit-learn) — chosen for interpretability and speed. Suitable for service metrics that follow cyclical (daily/weekly) patterns.

### Features engineered per service metric

| Feature | Description |
|---|---|
| `time_index` | Hours elapsed since first check — captures long-term trend |
| `hour`, `minute` | Time of day — captures daily cycles |
| `day_of_week`, `day_of_month` | Captures weekly/monthly patterns |
| `is_weekend` | Binary flag for Saturday/Sunday |
| `{metric}_lag1/3/6/12` | Previous values at 5min / 15min / 30min / 1hr ago |
| `{metric}_roll_mean_12` | 1-hour rolling average — smoothed recent level |
| `{metric}_roll_std_12` | 1-hour rolling standard deviation — recent volatility |
| `{metric}_roll_mean_36` | 3-hour rolling average — medium-term trend |
| `{metric}_roll_max_12` | 1-hour rolling max — recent peak load |
| `is_warning`, `is_critical` | Binary flags from Nagios check state |

### Train / test split
- 80% train / 20% test, **time-ordered** (no shuffle) — the test set is always the most recent data, which reflects real-world forecasting conditions.

### Forecast method
Auto-regressive 5-minute step loop — each predicted value is fed back as the lag input for the next step. This allows arbitrarily long forecasts from a single trained model.

---

## Caching & Lazy Training

The cache is keyed on `(host, service)` tuples:

```
model_cache[(host, service)] = {
    model, scaler, data, metrics,
    forecast_df, days_ahead,
    y_test, y_pred, cached_at
}
```

- **Cache miss** (first request for a pair) → trains automatically, stores result, returns response
- **Cache hit** → serves instantly from memory
- **Invalidation** → `DELETE /hosts/cache?host=X&service=Y`
- **Force retrain** → `POST /hosts/X/services/Y/train?force=true`
- **Server restart** → cache is empty; models retrain on first request per pair

---

## Scheduled Retraining

A background cron job (APScheduler) runs daily at the configured `RETRAIN_HOUR:RETRAIN_MINUTE` UTC. It retrains **every pair currently in the cache** with fresh data from the database.

```
RETRAIN_HOUR=2
RETRAIN_MINUTE=0
→ Retrains all cached (host, service) pairs at 02:00 UTC every day
```

If the server was offline at the scheduled time, APScheduler will fire the job when the server comes back up (within a 1-hour grace window).

---

## Database Schema Reference

The backend joins these four tables:

```
nagios_hosts
  └─ host_object_id, alias (host display name)

nagios_services
  └─ host_object_id (FK → nagios_hosts)
  └─ service_object_id
  └─ display_name (service display name)

nagios_servicechecks
  └─ service_object_id (FK → nagios_services)
  └─ start_time, state, state_type, output, perfdata

nagios_objects
  └─ object_id, name1, name2 (used for reference / UI labels)
```

The key SQL query that drives all data endpoints:

```sql
SELECT
    h.alias           AS host_name,
    s.display_name    AS service_name,
    sc.start_time     AS check_time,
    sc.state          AS check_state,
    sc.state_type     AS state_type,
    sc.output         AS check_output,
    sc.perfdata       AS perf_data,
    sc.execution_time AS execution_time,
    sc.return_code    AS return_code
FROM nagios_hosts h
JOIN nagios_services s
    ON s.host_object_id = h.host_object_id
JOIN nagios_servicechecks sc
    ON sc.service_object_id = s.service_object_id
WHERE h.alias = ?              -- host param
  AND s.display_name = ?       -- service param
  AND sc.start_time >= (SELECT MAX(start_time) FROM nagios_servicechecks)
      - INTERVAL ? DAY         -- history window
  AND sc.early_timeout = 0
ORDER BY h.alias ASC, sc.start_time ASC
```

---

## FAQ

**Q: The first request for a new (host, service) is slow. Why?**

Training is triggered synchronously on the first request. For 30 days of 5-minute checks (~8,600 rows), this typically takes 1–3 seconds. Pre-warm any pairs you know users will hit with `POST /hosts/{host}/services/{service}/train` at startup.

**Q: Can I forecast more than 7 days?**

Yes — all forecast/summary/combined endpoints accept `?days=1` through `?days=30`.

**Q: What if perfdata has multiple metrics (e.g. `power=1240W temp=25C`)?**

The first parsed metric becomes the forecast target. Currently one target per model. To forecast a specific metric (e.g. temperature), ensure the service only returns that metric, or the code can be extended to accept a `?metric=` parameter.

**Q: The host name isn't matching. What should I check?**

The `host` parameter must match `nagios_hosts.alias` exactly (case-sensitive). Run `GET /hosts/` to see the exact strings stored in your database.

**Q: Can I run multiple workers?**

Yes with a caveat — the in-memory cache is per-process. With `--workers 2`, each worker has its own cache so the first request per worker per pair will trigger training. For production multi-worker deployments, consider replacing `cache.py` with a Redis-backed cache.
