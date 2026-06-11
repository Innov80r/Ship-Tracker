"""
Time formatting utilities.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional


def utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def format_eta(eta: Optional[datetime]) -> Optional[str]:
    """Format ETA as human-readable string."""
    if eta is None:
        return None
    return eta.strftime("%Y-%m-%d %H:%M UTC")


def time_ago(dt: Optional[datetime]) -> str:
    """Return a human-readable 'time ago' string."""
    if dt is None:
        return "N/A"
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 0:
        return "just now"
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


def format_duration_hours(hours: Optional[float]) -> str:
    """Format duration in hours to human-readable string."""
    if hours is None:
        return "N/A"
    if hours < 1:
        return f"{int(hours * 60)}m"
    if hours < 24:
        return f"{hours:.1f}h"
    days = hours / 24
    return f"{days:.1f}d"


def parse_ais_eta(month: int, day: int, hour: int, minute: int) -> Optional[datetime]:
    """
    Parse ETA from AIS message fields (month, day, hour, minute).
    AIS ETA has no year — we assume the closest future date.
    """
    if month == 0 or day == 0:
        return None
    now = utcnow()
    year = now.year
    try:
        eta = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
        if eta < now:
            eta = eta.replace(year=year + 1)
        return eta
    except (ValueError, OverflowError):
        return None
