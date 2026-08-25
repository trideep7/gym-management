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
