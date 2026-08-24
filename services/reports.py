import datetime

from services import attendance, payments


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
