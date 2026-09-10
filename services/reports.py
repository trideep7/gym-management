import datetime

from services import attendance, payments, trainers


def signin_counts(conn, start_date, end_date):
    counts_by_date = {row["date"]: row["count"] for row in attendance.counts_by_day(conn, start_date, end_date)}
    start = datetime.date.fromisoformat(start_date)
    end = datetime.date.fromisoformat(end_date)
    result = []
    day = start
    while day <= end:
        date_str = day.isoformat()
        result.append({"date": date_str, "count": counts_by_date.get(date_str, 0)})
        day += datetime.timedelta(days=1)
    return result


def payment_summary(conn):
    entries = payments.list_members_with_status(conn)
    summary = {
        "paid": 0,
        "overdue": 0,
        "no_payment": 0,
        "overdue_members": [],
        "no_payment_members": [],
    }
    for entry in entries:
        summary[entry["status"]] += 1
        if entry["status"] == "overdue":
            summary["overdue_members"].append(entry)
        elif entry["status"] == "no_payment":
            summary["no_payment_members"].append(entry)
    return summary


def most_active_members(conn, start_date, end_date, limit=10):
    return attendance.most_active(conn, start_date, end_date, limit)


def due_summary(conn):
    return payments.due_amounts(conn)


def daily_revenue(conn, start_date, end_date):
    totals_by_date = {row["date"]: row["total"] for row in payments.revenue_by_day(conn, start_date, end_date)}
    start = datetime.date.fromisoformat(start_date)
    end = datetime.date.fromisoformat(end_date)
    result = []
    day = start
    while day <= end:
        date_str = day.isoformat()
        result.append({"date": date_str, "total": totals_by_date.get(date_str, 0)})
        day += datetime.timedelta(days=1)
    return result


def _months_before_start(today, months_back):
    year = today.year
    month = today.month - months_back
    while month <= 0:
        month += 12
        year -= 1
    return datetime.date(year, month, 1)


def _month_keys(start, end):
    year, month = start.year, start.month
    keys = []
    while (year, month) <= (end.year, end.month):
        keys.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            month = 1
            year += 1
    return keys


def monthly_revenue_trend(conn, today=None, months=12):
    today = today or datetime.date.today()
    start = _months_before_start(today, months - 1)
    totals_by_month = {row["month"]: row["total"] for row in payments.revenue_by_month(conn, start.isoformat(), today.isoformat())}
    return [{"month": key, "total": totals_by_month.get(key, 0)} for key in _month_keys(start, today)]


def _month_end(d):
    if d.month == 12:
        next_month_first = datetime.date(d.year + 1, 1, 1)
    else:
        next_month_first = datetime.date(d.year, d.month + 1, 1)
    return next_month_first - datetime.timedelta(days=1)


def overview_stats(conn, today=None):
    today = today or datetime.date.today()
    month_start = today.replace(day=1)
    month_end = _month_end(today)
    year_start = today.replace(month=1, day=1)
    year_end = today.replace(month=12, day=31)
    three_months_ago = (today - datetime.timedelta(days=90)).isoformat()
    due = due_summary(conn)
    return {
        # bounded on both ends -- a member paying ahead for a future cycle
        # must not inflate this month's (or year's) total before that
        # period actually arrives
        "revenue_this_month": payments.revenue_between(conn, month_start.isoformat(), month_end.isoformat()),
        "revenue_this_year": payments.revenue_between(conn, year_start.isoformat(), year_end.isoformat()),
        "active_members": attendance.active_since_count(conn, three_months_ago),
        "payments_overdue": payment_summary(conn)["overdue"],
        "due_active": due["active"],
    }


def payment_method_breakdown_this_month(conn, today=None):
    today = today or datetime.date.today()
    month_start = today.replace(day=1)
    month_end = _month_end(today)
    return payments.payment_method_breakdown(conn, month_start.isoformat(), month_end.isoformat())


def pt_summary(conn, start_date, end_date):
    return trainers.pt_summary(conn, start_date, end_date)


def trainer_payouts(conn, start_date, end_date):
    return trainers.trainer_payouts(conn, start_date, end_date)
