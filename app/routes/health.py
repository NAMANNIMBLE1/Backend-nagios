from fastapi import APIRouter
from datetime import datetime, timezone

from app.cache import model_cache
from app.scheduler import scheduler
from db.db_connection import get_sql_data
from app.schemas.response import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", response_model=HealthResponse, summary="System health check")
def health_check():
    """
    Returns live status of:
    - Database connectivity
    - Data availability (row count + date range)
    - Model pipeline readiness (from cache)
    - Last training time + next scheduled retrain
    """
    db_connected = False
    data_rows    = 0
    data_start   = None
    data_end     = None

    # ── Check DB (always live — tells us if DB is reachable right now) ──
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

    # ── Check model (read from cache — no re-training) ──
    cache       = model_cache.get_cache()
    model_ready = model_cache.is_ready()
    cached_at   = model_cache.get_cached_at()

    # ── Next scheduled retrain from APScheduler ──
    next_retrain = None
    try:
        job = scheduler.get_job("daily_retrain")
        if job and job.next_run_time:
            next_retrain = job.next_run_time.isoformat()
    except Exception:
        pass

    # ── Pull data range from cache if DB check didn't get it ──
    if not data_start and model_ready:
        df_full = cache["data"].get("df_full")
        if df_full is not None and "check_time" in df_full.columns:
            data_start = str(df_full["check_time"].min())
            data_end   = str(df_full["check_time"].max())
            data_rows  = data_rows or len(df_full)

    return HealthResponse(
        status          = "ok" if (db_connected and model_ready) else "degraded",
        timestamp       = datetime.now(timezone.utc).isoformat(),
        db_connected    = db_connected,
        model_ready     = model_ready,
        data_rows       = data_rows,
        data_start      = data_start,
        data_end        = data_end,
        last_trained_at = cached_at,
        next_retrain_at = next_retrain,
    )