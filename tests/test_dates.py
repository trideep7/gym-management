import datetime

from utils.dates import format_date


def test_format_date_from_iso_string():
    assert format_date("2026-08-25") == "25-Aug-2026"


def test_format_date_from_date_object():
    assert format_date(datetime.date(2026, 1, 5)) == "05-Jan-2026"


def test_format_date_none_returns_dash():
    assert format_date(None) == "—"


def test_format_date_empty_string_returns_dash():
    assert format_date("") == "—"
