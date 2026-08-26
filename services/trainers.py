import datetime

PT_TRAINER_SHARE = 2000  # of payments.PT_MONTHLY_FEE (3000) per month; the rest is the gym's share


def create_trainer(conn, name, mobile, time_slot):
    cursor = conn.execute(
        "INSERT INTO trainers (name, mobile, time_slot, is_active, created_at) VALUES (?, ?, ?, 1, ?)",
        (name, mobile, time_slot, datetime.datetime.now().isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def list_trainers(conn, active_only=True):
    sql = "SELECT * FROM trainers"
    if active_only:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY name"
    return [dict(r) for r in conn.execute(sql).fetchall()]


def update_trainer(conn, trainer_id, name, mobile, time_slot):
    conn.execute(
        "UPDATE trainers SET name = ?, mobile = ?, time_slot = ? WHERE id = ?",
        (name, mobile, time_slot, trainer_id),
    )
    conn.commit()


def set_trainer_active(conn, trainer_id, is_active):
    conn.execute("UPDATE trainers SET is_active = ? WHERE id = ?", (1 if is_active else 0, trainer_id))
    conn.commit()


def delete_trainer(conn, trainer_id):
    payment_count = conn.execute(
        "SELECT COUNT(*) AS c FROM trainer_payments WHERE trainer_id = ?", (trainer_id,)
    ).fetchone()["c"]
    member_count = conn.execute(
        "SELECT COUNT(*) AS c FROM members WHERE trainer_id = ?", (trainer_id,)
    ).fetchone()["c"]
    if payment_count > 0 or member_count > 0:
        set_trainer_active(conn, trainer_id, False)
        return "deactivated"
    conn.execute("DELETE FROM trainers WHERE id = ?", (trainer_id,))
    conn.commit()
    return "deleted"
