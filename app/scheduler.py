import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config.get_config import get_config

logger    = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="UTC")


def _retrain():
    """Wrapper so the import happens at call time (avoids circular imports)."""
    from app.services.training_service import retrain_all_cached
    # Snapshot cache before retraining (optional, for backup/audit)
    try:
        from app.cache.model_cache import model_cache
        import pickle, os
        snapshot_path = os.path.join(os.path.dirname(__file__), '../cache/cache_snapshot.pkl')
        with open(snapshot_path, 'wb') as f:
            pickle.dump(model_cache._store, f)
        logger.info("[Scheduler] Cache snapshot saved before retraining.")
    except Exception as e:
        logger.warning(f"[Scheduler] Failed to snapshot cache: {e}")
    retrain_all_cached()


def start_scheduler() -> None:
    config = get_config()
    hour   = int(config.get("RETRAIN_HOUR",   2))
    minute = int(config.get("RETRAIN_MINUTE", 0))

    scheduler.add_job(
        func               = _retrain,
        trigger            = CronTrigger(hour=hour, minute=minute, timezone="UTC"),
        id                 = "daily_retrain",
        replace_existing   = True,
        misfire_grace_time = 3600,
    )
    scheduler.start()
    logger.info("[Scheduler] Daily retrain at %02d:%02d UTC", hour, minute)


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
