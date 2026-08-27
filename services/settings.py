"""Key/value gym configuration.

Values are stored as TEXT and parsed on read, so a hand-edited database
can't crash a page load with a stray non-numeric value -- readers fall
back to the documented default instead.
"""

LOCKER_COUNT_KEY = "locker_count"
RENEWAL_GRACE_DAYS_KEY = "renewal_grace_days"

# 0 means "no limit set", not "zero lockers". Any existing database starts
# here, and blocking every locker assignment until an admin visits Settings
# would lock staff out of editing members who already hold one.
DEFAULT_LOCKER_COUNT = 0
DEFAULT_RENEWAL_GRACE_DAYS = 7


def get_setting(conn, key, default=None):
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return default if row is None else row["value"]


def set_setting(conn, key, value):
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    conn.commit()


def get_int_setting(conn, key, default):
    raw = get_setting(conn, key)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def get_locker_count(conn):
    return get_int_setting(conn, LOCKER_COUNT_KEY, DEFAULT_LOCKER_COUNT)


def set_locker_count(conn, count):
    count = int(count)
    if count < 0:
        raise ValueError("Locker count can't be negative.")
    set_setting(conn, LOCKER_COUNT_KEY, count)


def lockers_in_use(conn, exclude_member_id=None):
    """How many active members currently hold a locker.

    `exclude_member_id` leaves one member out of the count, so editing
    someone who already holds a locker doesn't count them against the
    total and block their own save.
    """
    sql = "SELECT COUNT(*) AS c FROM members WHERE has_locker = 1 AND is_active = 1"
    params = []
    if exclude_member_id is not None:
        sql += " AND id != ?"
        params.append(exclude_member_id)
    return conn.execute(sql, params).fetchone()["c"]


def get_renewal_grace_days(conn):
    return get_int_setting(conn, RENEWAL_GRACE_DAYS_KEY, DEFAULT_RENEWAL_GRACE_DAYS)


def set_renewal_grace_days(conn, days):
    days = int(days)
    if days < 0:
        raise ValueError("Grace window can't be negative.")
    set_setting(conn, RENEWAL_GRACE_DAYS_KEY, days)
