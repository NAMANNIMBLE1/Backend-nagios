from fastapi import APIRouter
from datetime import datetime, timezone

from app.controllers.data_processing import prediction_tabular_data
from db.db_connection import get_sql_data
from app.schemas.response import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", response_model=HealthResponse, summary="System health check")
def health_check():
    """
    Returns live status of:
    - Database connectivity
    - Data availability (row count + date range)
    - Model pipeline readiness
    """
    db_connected = False
    model_ready  = False
    data_rows    = 0
    data_start   = None
    data_end     = None

    # ── Check DB ──
    try:
        result   = get_sql_data()
        rows     = result.get("rows", [])
        columns  = result.get("columns", [])
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

    # ── Check model pipeline ──
    try:
        data        = prediction_tabular_data()
        model_ready = data["X"].shape[0] > 0
    except Exception:
        pass

    return HealthResponse(
        status       = "ok" if (db_connected and model_ready) else "degraded",
        timestamp    = datetime.now(timezone.utc).isoformat(),
        db_connected = db_connected,
        model_ready  = model_ready,
        data_rows    = data_rows,
        data_start   = data_start,
        data_end     = data_end,
    )