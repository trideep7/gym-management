import datetime

from utils.dates import format_date, format_time


def test_format_date_from_iso_string():
    assert format_date("2026-08-25") == "25-Aug-2026"


def test_format_date_from_date_object():
    assert format_date(datetime.date(2026, 1, 5)) == "05-Jan-2026"


def test_format_date_none_returns_dash():
    assert format_date(None) == "—"


def test_format_date_empty_string_returns_dash():
    assert format_date("") == "—"


def test_format_time_morning():
    assert format_time("09:05:00") == "09:05 AM"


def test_format_time_afternoon():
    assert format_time("14:32:07") == "02:32 PM"


def test_format_time_noon():
    assert format_time("12:00:00") == "12:00 PM"


def test_format_time_midnight():
    assert format_time("00:00:00") == "12:00 AM"


def test_format_time_none_returns_dash():
    assert format_time(None) == "—"
