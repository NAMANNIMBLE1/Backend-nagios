import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.training_service import run_training_pipeline
from config.get_config import get_config

logger    = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="UTC")


def start_scheduler() -> None:
    config = get_config()
    hour   = int(config.get("RETRAIN_HOUR",   2))  # read from .env
    minute = int(config.get("RETRAIN_MINUTE", 0))

    scheduler.add_job(
        func             = run_training_pipeline,  # ← function to call
        trigger          = CronTrigger(hour=hour, minute=minute, timezone="UTC"),
        id               = "daily_retrain",
        replace_existing = True,
        misfire_grace_time = 3600,  # if server was down at 2am, run when it wakes up
    )
    scheduler.start()
    logger.info(f"[Scheduler] Daily retrain at {hour:02d}:{minute:02d} UTC")


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)