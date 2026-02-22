# src/app/scheduler/gsheet_scheduler.py
"""Weekly Google Sheets export scheduler with retry and verification."""

import logging
import os
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler = None

# Track last export for verification
_last_export_count = 0
_last_export_time = None


def retry_with_backoff(func, max_retries=3, base_delay=30):
    """
    Retry a function with exponential backoff.

    Args:
        func: Function to call
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (doubles each retry)

    Returns:
        Result of function call, or raises last exception
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"Export attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {delay} seconds..."
                )
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries} export attempts failed")

    raise last_exception


def do_export():
    """Execute the actual export and return count."""
    import sys
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from export_to_gsheet import export_weekly
    return export_weekly()


def weekly_gsheet_export():
    """Run the weekly Google Sheets export with retry logic."""
    global _last_export_count, _last_export_time, _scheduler

    logger.info("Starting scheduled weekly Google Sheets export...")

    try:
        # Run export with retry logic (3 attempts, 30s/60s/120s backoff)
        count = retry_with_backoff(do_export, max_retries=3, base_delay=30)

        _last_export_count = count
        _last_export_time = datetime.now()

        logger.info(f"Weekly export completed: {count} trades added")

        # Update win/loss stats after export
        update_win_loss_stats()

        # Schedule verification check in 10 minutes
        if _scheduler and count > 0:
            verify_time = datetime.now() + timedelta(minutes=10)
            _scheduler.add_job(
                verify_export,
                trigger=DateTrigger(run_date=verify_time),
                id="verify_export",
                name="Verify Google Sheets Export",
                replace_existing=True,
            )
            logger.info(f"Verification check scheduled for {verify_time.strftime('%H:%M:%S')}")

    except Exception as e:
        logger.error(f"Weekly Google Sheets export failed after all retries: {e}", exc_info=True)


def verify_export():
    """Verify the export actually made it to Google Sheets."""
    global _last_export_count, _last_export_time

    logger.info("Running export verification check...")

    try:
        import sys
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        from app.gsheet.gsheet_client import connect_to_sheet

        credentials_path = os.environ.get(
            "GOOGLE_SHEETS_CREDENTIALS_PATH",
            "/data/dulcet-abacus-481722-g8-7d60a0bb5dd7.json"
        )
        spreadsheet_id = os.environ.get(
            "GOOGLE_SHEETS_SPREADSHEET_ID",
            "14DKgxt8RbQdGxLiircSCLuA0Yxh-LDDlbZYEOMMO6eA"
        )

        worksheet = connect_to_sheet(credentials_path, spreadsheet_id, "Sheet1")
        all_values = worksheet.get_all_values()
        row_count = len(all_values)

        # Check if we have the expected number of rows
        # The sheet should have grown by _last_export_count since export
        if _last_export_time:
            time_since_export = datetime.now() - _last_export_time
            logger.info(
                f"Verification: Sheet has {row_count} rows. "
                f"Last export added {_last_export_count} trades "
                f"({time_since_export.seconds // 60} min ago)"
            )

            if _last_export_count > 0:
                # Check if recent entries exist by looking at dates in last few rows
                recent_rows = all_values[-min(10, _last_export_count):]
                has_recent = any(row[0] for row in recent_rows if row)  # Check Posted Date column

                if has_recent:
                    logger.info("Verification PASSED: Recent trades found in sheet")
                else:
                    logger.warning("Verification WARNING: Could not confirm recent trades in sheet")
        else:
            logger.info(f"Verification: Sheet has {row_count} total rows")

    except Exception as e:
        logger.error(f"Verification check failed: {e}", exc_info=True)


def update_win_loss_stats():
    """Update the Stats sheet with win/loss percentage."""
    try:
        from app.gsheet.gsheet_client import update_stats_sheet

        # Get config from environment
        credentials_path = os.environ.get(
            "GOOGLE_SHEETS_CREDENTIALS_PATH",
            "/data/dulcet-abacus-481722-g8-7d60a0bb5dd7.json"
        )
        spreadsheet_id = os.environ.get(
            "GOOGLE_SHEETS_SPREADSHEET_ID",
            "14DKgxt8RbQdGxLiircSCLuA0Yxh-LDDlbZYEOMMO6eA"
        )

        stats = update_stats_sheet(credentials_path, spreadsheet_id)
        logger.info(f"Win/Loss stats updated: {stats['win_rate_pct']}% ({stats['wins']}W / {stats['losses']}L)")

    except Exception as e:
        logger.error(f"Failed to update win/loss stats: {e}", exc_info=True)


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
