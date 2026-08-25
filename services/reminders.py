import datetime


def log_reminder(conn, member_id, sent_by):
    cursor = conn.execute(
        "INSERT INTO payment_reminders (member_id, sent_by, sent_at) VALUES (?, ?, ?)",
        (member_id, sent_by, datetime.datetime.now().isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def list_reminders(conn, member_id):
    rows = conn.execute(
        "SELECT payment_reminders.*, users.full_name AS sent_by_name FROM payment_reminders "
        "JOIN users ON payment_reminders.sent_by = users.id "
        "WHERE member_id = ? ORDER BY sent_at DESC",
        (member_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def last_reminder(conn, member_id):
    row = conn.execute(
        "SELECT payment_reminders.*, users.full_name AS sent_by_name FROM payment_reminders "
        "JOIN users ON payment_reminders.sent_by = users.id "
        "WHERE member_id = ? ORDER BY sent_at DESC LIMIT 1",
        (member_id,),
    ).fetchone()
    return dict(row) if row else None
