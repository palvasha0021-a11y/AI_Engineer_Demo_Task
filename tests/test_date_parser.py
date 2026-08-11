from datetime import datetime, timedelta, timezone
from src.utils.date_parser import parse_date, is_within_last_24_hours


def test_parse_date_relative_hours():
    dt = parse_date("2 hours ago")
    assert dt is not None
    assert is_within_last_24_hours(dt, hours=24) is True


def test_parse_date_relative_days_old():
    dt = parse_date("3 days ago")
    assert dt is not None
    assert is_within_last_24_hours(dt, hours=24) is False


def test_parse_date_iso_format():
    now = datetime.now(timezone.utc)
    iso_str = now.isoformat()
    dt = parse_date(iso_str)
    assert dt is not None
    assert is_within_last_24_hours(dt, hours=24) is True


def test_is_within_last_24_hours_boundary():
    now = datetime.now(timezone.utc)
    twenty_three_hours_ago = now - timedelta(hours=23)
    twenty_five_hours_ago = now - timedelta(hours=25)

    assert is_within_last_24_hours(twenty_three_hours_ago) is True
    assert is_within_last_24_hours(twenty_five_hours_ago) is False
