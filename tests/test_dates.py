import datetime

import pytest

from utils.dates import format_date, format_time, preset_range


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


def test_preset_range_today():
    today = datetime.date(2026, 8, 26)
    assert preset_range("Today", today) == (today, today)


def test_preset_range_yesterday():
    today = datetime.date(2026, 8, 26)
    assert preset_range("Yesterday", today) == (datetime.date(2026, 8, 25), datetime.date(2026, 8, 25))


def test_preset_range_last_7_days():
    today = datetime.date(2026, 8, 26)
    assert preset_range("Last 7 Days", today) == (datetime.date(2026, 8, 20), today)


def test_preset_range_this_month():
    today = datetime.date(2026, 8, 26)
    assert preset_range("This Month", today) == (datetime.date(2026, 8, 1), today)


def test_preset_range_last_month_mid_year():
    today = datetime.date(2026, 8, 15)
    assert preset_range("Last Month", today) == (datetime.date(2026, 7, 1), datetime.date(2026, 7, 31))


def test_preset_range_last_month_from_first_of_january():
    today = datetime.date(2026, 1, 1)
    assert preset_range("Last Month", today) == (datetime.date(2025, 12, 1), datetime.date(2025, 12, 31))


def test_preset_range_this_year():
    today = datetime.date(2026, 8, 26)
    assert preset_range("This Year", today) == (datetime.date(2026, 1, 1), today)


def test_preset_range_unknown_preset_raises():
    with pytest.raises(ValueError):
        preset_range("Not A Real Preset", datetime.date(2026, 8, 26))
