import datetime


def format_date(value):
    if not value:
        return "—"
    if isinstance(value, str):
        value = datetime.date.fromisoformat(value)
    return value.strftime("%d-%b-%Y")
