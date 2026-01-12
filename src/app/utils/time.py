#/usr/bin/env python3
from datetime import datetime, timedelta, timezone

def time_delta_to_iso_days(delta_days: int) -> str:
    #format yyyy-MM-dd'T'HH:mm:ss.SSSZ. Example: 2023-10-05T14:48:00.000Z
    target_date = datetime.now(timezone.utc) - timedelta(days=delta_days)
    current_date = datetime.now(timezone.utc)
    return target_date.isoformat(), current_date.isoformat()