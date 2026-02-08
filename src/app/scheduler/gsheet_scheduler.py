# src/app/scheduler/gsheet_scheduler.py
"""Weekly Google Sheets export scheduler."""

import logging
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler = None


def weekly_gsheet_export():
    """Run the weekly Google Sheets export."""
    logger.info("Starting scheduled weekly Google Sheets export...")
    try:
        # Import here to avoid circular imports
        import sys
        import os

        # Add the project root to path if needed
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        from export_to_gsheet import export_weekly
        count = export_weekly()
        logger.info(f"Weekly export completed: {count} trades added")
    except Exception as e:
        logger.error(f"Weekly Google Sheets export failed: {e}", exc_info=True)


def start_gsheet_scheduler(day_of_week: str = "sun", hour: int = 20, minute: int = 0):
    """
    Start the weekly Google Sheets export scheduler.

    Args:
        day_of_week: Day to run (mon, tue, wed, thu, fri, sat, sun)
        hour: Hour to run (0-23)
        minute: Minute to run (0-59)

    Default: Sundays at 8:00 PM
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler already running")
        return _scheduler

    # Allow override from environment
    day_of_week = os.environ.get("GSHEET_EXPORT_DAY", day_of_week)
    hour = int(os.environ.get("GSHEET_EXPORT_HOUR", hour))
    minute = int(os.environ.get("GSHEET_EXPORT_MINUTE", minute))

    _scheduler = BackgroundScheduler()

    # Add weekly job
    _scheduler.add_job(
        weekly_gsheet_export,
        trigger=CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute),
        id="weekly_gsheet_export",
        name="Weekly Google Sheets Export",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(f"Google Sheets scheduler started: runs every {day_of_week} at {hour:02d}:{minute:02d}")

    return _scheduler


def stop_gsheet_scheduler():
    """Stop the Google Sheets export scheduler."""
    global _scheduler

    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Google Sheets scheduler stopped")


def run_export_now():
    """Manually trigger the weekly export immediately."""
    logger.info("Manual export triggered")
    weekly_gsheet_export()
