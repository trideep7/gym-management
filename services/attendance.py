import datetime
import sqlite3


def sign_in(conn, member_id, recorded_by, when=None):
    now = when or datetime.datetime.now()
    date_str = now.date().isoformat()
    time_str = now.time().strftime("%H:%M:%S")
    existing = conn.execute(
        "SELECT sign_in_time FROM attendance WHERE member_id = ? AND sign_in_date = ?",
        (member_id, date_str),
    ).fetchone()
    if existing:
        return {"already_signed_in": True, "sign_in_time": existing["sign_in_time"]}
    try:
        conn.execute(
            "INSERT INTO attendance (member_id, sign_in_date, sign_in_time, recorded_by) VALUES (?, ?, ?, ?)",
            (member_id, date_str, time_str, recorded_by),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Another request won the race between our check above and this
        # INSERT — re-read the row it created and resolve the same way the
        # normal duplicate-sign-in path does.
        existing = conn.execute(
            "SELECT sign_in_time FROM attendance WHERE member_id = ? AND sign_in_date = ?",
            (member_id, date_str),
        ).fetchone()
        return {"already_signed_in": True, "sign_in_time": existing["sign_in_time"]}
    return {"already_signed_in": False, "sign_in_time": time_str}


def list_today(conn):
    today = datetime.date.today().isoformat()
    rows = conn.execute(
        "SELECT attendance.*, members.first_name, members.surname, members.mobile FROM attendance "
        "JOIN members ON attendance.member_id = members.id "
        "WHERE sign_in_date = ? ORDER BY sign_in_time DESC",
        (today,),
    ).fetchall()
    return [dict(r) for r in rows]


def member_history(conn, member_id, limit=None):
    sql = (
        "SELECT * FROM attendance WHERE member_id = ? "
        "ORDER BY sign_in_date DESC, sign_in_time DESC"
    )
    params = [member_id]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def counts_by_day(conn, start_date, end_date):
    rows = conn.execute(
        "SELECT sign_in_date AS date, COUNT(*) AS count FROM attendance "
        "WHERE sign_in_date BETWEEN ? AND ? GROUP BY sign_in_date ORDER BY sign_in_date",
        (start_date, end_date),
    ).fetchall()
    return [dict(r) for r in rows]


def active_since_count(conn, since_date):
    row = conn.execute(
        "SELECT COUNT(DISTINCT attendance.member_id) AS c FROM attendance "
        "JOIN members ON attendance.member_id = members.id "
        "WHERE attendance.sign_in_date >= ? AND members.is_active = 1",
        (since_date,),
    ).fetchone()
    return row["c"]


def most_active(conn, start_date, end_date, limit=10):
    rows = conn.execute(
        "SELECT members.id AS member_id, members.first_name, members.surname, COUNT(*) AS checkins "
        "FROM attendance JOIN members ON attendance.member_id = members.id "
        "WHERE sign_in_date BETWEEN ? AND ? "
        "GROUP BY members.id ORDER BY checkins DESC LIMIT ?",
        (start_date, end_date, limit),
    ).fetchall()
    return [dict(r) for r in rows]
