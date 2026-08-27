import datetime


def format_date(value):
    if not value:
        return "—"
    if isinstance(value, str):
        value = datetime.date.fromisoformat(value)
    return value.strftime("%d-%b-%Y")


def format_time(value):
    if not value:
        return "—"
    if isinstance(value, str):
        value = datetime.datetime.strptime(value, "%H:%M:%S").time()
    return value.strftime("%I:%M %p")


def preset_range(preset, today=None):
    today = today or datetime.date.today()
    if preset == "Today":
        return today, today
    if preset == "Yesterday":
        yesterday = today - datetime.timedelta(days=1)
        return yesterday, yesterday
    if preset == "Last 7 Days":
        return today - datetime.timedelta(days=6), today
    if preset == "This Month":
        return today.replace(day=1), today
    if preset == "Last Month":
        last_month_end = today.replace(day=1) - datetime.timedelta(days=1)
        return last_month_end.replace(day=1), last_month_end
    if preset == "This Year":
        return today.replace(month=1, day=1), today
    raise ValueError(f"Unknown preset: {preset}")
