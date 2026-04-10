from datetime import datetime, timezone
from fastapi import APIRouter

from app.cache.model_cache import model_cache
from app.scheduler import scheduler
from app.schemas.response import HealthResponse
from db.db_connection import get_sql_data

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", response_model=HealthResponse, summary="System health check")
def health_check():
    db_connected = False
    data_rows    = 0
    data_start   = None
    data_end     = None

    # ── live DB probe ──
    try:
        result       = get_sql_data()
        rows         = result.get("rows", [])
        columns      = result.get("columns", [])
        db_connected = True
        data_rows    = len(rows)

        if rows and "check_time" in columns:
            idx   = columns.index("check_time")
            times = [r[idx] for r in rows if r[idx] is not None]
            if times:
                data_start = str(min(times))
                data_end   = str(max(times))
    except Exception:
        pass

    # ── cache status ──
    cached_keys    = model_cache.cached_keys()
    cached_entries = len(cached_keys)
    model_ready    = cached_entries > 0

    # last trained = most recent cached_at across all entries
    last_trained = None
    if cached_keys:
        last_trained = max(e["cached_at"] for e in cached_keys)

    # fall back to first cache entry for data range if DB probe got nothing
    if not data_start and model_ready:
        first = model_cache.get_cache(cached_keys[0]["host"], cached_keys[0]["service"])
        if first:
            df_full = first["data"].get("df_full")
            if df_full is not None and "check_time" in df_full.columns:
                data_start = str(df_full["check_time"].min())
                data_end   = str(df_full["check_time"].max())
                data_rows  = data_rows or len(df_full)

    # ── next scheduled retrain ──
    next_retrain = None
    try:
        job = scheduler.get_job("daily_retrain")
        if job and job.next_run_time:
            next_retrain = job.next_run_time.isoformat()
    except Exception:
        pass

    return HealthResponse(
        status          = "ok" if (db_connected and model_ready) else "degraded",
        timestamp       = datetime.now(timezone.utc).isoformat(),
        db_connected    = db_connected,
        model_ready     = model_ready,
        cached_entries  = cached_entries,
        data_rows       = data_rows,
        data_start      = data_start,
        data_end        = data_end,
        last_trained_at = last_trained,
        next_retrain_at = next_retrain,
    )
