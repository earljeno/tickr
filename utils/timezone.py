from datetime import datetime
from zoneinfo import ZoneInfo

MANILA_TZ = ZoneInfo("Asia/Manila")


def get_now() -> datetime:
    """Return the current datetime localized to Asia/Manila."""
    return datetime.now(MANILA_TZ)


def get_time_ago(log_time: datetime | None) -> str:
    """Convert a datetime object into a relative 'X minutes ago' string.

    Safely handles naive and timezone-aware datetimes.
    """
    if log_time is None:
        return "Unknown"

    now = get_now()

    # Handle timezone mismatch if log_time from DB is naive
    if log_time.tzinfo is None:
        log_time = log_time.replace(tzinfo=MANILA_TZ)

    diff = now - log_time
    seconds = diff.total_seconds()

    if seconds < 0:
        return "Just now"
    if seconds < 60:
        return "Just now"
    if seconds < 3600:
        mins = int(seconds // 60)
        return f"{mins} minute{'s' if mins != 1 else ''} ago"
    if seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

    days = int(seconds // 86400)
    return f"{days} day{'s' if days != 1 else ''} ago"
