import re
from datetime import datetime, timedelta, timezone
from typing import Optional


def parse_date(date_str: Optional[str], default_now: bool = False) -> Optional[datetime]:
    """Parse various date formats (ISO-8601, relative strings, standard dates) into UTC datetime."""
    if not date_str:
        return datetime.now(timezone.utc) if default_now else None

    date_str = date_str.strip().lower()

    # 1. Handle relative dates like "X hours ago", "X mins ago", "yesterday"
    if "ago" in date_str or "yesterday" in date_str:
        now = datetime.now(timezone.utc)
        if "yesterday" in date_str:
            return now - timedelta(days=1)

        match = re.search(r"(\d+)\s+(minute|min|hour|hr|day|sec|second)s?\s+ago", date_str)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            if "sec" in unit:
                return now - timedelta(seconds=amount)
            elif "min" in unit:
                return now - timedelta(minutes=amount)
            elif "hour" in unit or "hr" in unit:
                return now - timedelta(hours=amount)
            elif "day" in unit:
                return now - timedelta(days=amount)

    # 2. Try standard ISO-8601 formats
    clean_str = date_str.upper().replace("Z", "+00:00")
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
    ):
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass

    # Try ISO from isoformat
    try:
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass

    return datetime.now(timezone.utc) if default_now else None


def is_within_last_24_hours(dt: Optional[datetime], hours: int = 24) -> bool:
    """Check if a datetime falls within the last X hours (default 24h)."""
    if not dt:
        return False

    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    cutoff = now - timedelta(hours=hours)
    # Allow a small clock skew window (up to +1 hour in future)
    future_bound = now + timedelta(hours=1)
    return cutoff <= dt <= future_bound


def format_iso(dt: Optional[datetime]) -> str:
    """Format a datetime to standard ISO-8601 UTC string."""
    if not dt:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
