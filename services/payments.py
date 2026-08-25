import datetime


def create_plan(conn, name, amount, duration_days):
    cursor = conn.execute(
        "INSERT INTO membership_plans (name, amount, duration_days, is_active) VALUES (?, ?, ?, 1)",
        (name, amount, duration_days),
    )
    conn.commit()
    return cursor.lastrowid


def list_plans(conn, active_only=True):
    sql = "SELECT * FROM membership_plans"
    if active_only:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY name"
    return [dict(r) for r in conn.execute(sql).fetchall()]


def set_plan_active(conn, plan_id, is_active):
    conn.execute(
        "UPDATE membership_plans SET is_active = ? WHERE id = ?", (1 if is_active else 0, plan_id)
    )
    conn.commit()


def delete_plan(conn, plan_id):
    payment_count = conn.execute(
        "SELECT COUNT(*) AS c FROM payments WHERE plan_id = ?", (plan_id,)
    ).fetchone()["c"]
    member_count = conn.execute(
        "SELECT COUNT(*) AS c FROM members WHERE plan_id = ?", (plan_id,)
    ).fetchone()["c"]
    if payment_count > 0 or member_count > 0:
        set_plan_active(conn, plan_id, False)
        return "deactivated"
    conn.execute("DELETE FROM membership_plans WHERE id = ?", (plan_id,))
    conn.commit()
    return "deleted"


def mark_paid(conn, member_id, plan_id, recorded_by, paid_on=None):
    plan = conn.execute("SELECT * FROM membership_plans WHERE id = ?", (plan_id,)).fetchone()
    if plan is None:
        raise ValueError(f"No plan with id {plan_id}")

    if paid_on is None:
        paid_on_date = datetime.date.today()
    elif isinstance(paid_on, str):
        paid_on_date = datetime.date.fromisoformat(paid_on)
    else:
        paid_on_date = paid_on

    valid_until = paid_on_date + datetime.timedelta(days=plan["duration_days"])
    cursor = conn.execute(
        "INSERT INTO payments (member_id, plan_id, amount, paid_on, valid_until, recorded_by) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (member_id, plan_id, plan["amount"], paid_on_date.isoformat(), valid_until.isoformat(), recorded_by),
    )
    conn.commit()
    return cursor.lastrowid


def get_status(conn, member_id):
    row = conn.execute(
        "SELECT * FROM payments WHERE member_id = ? ORDER BY valid_until DESC LIMIT 1",
        (member_id,),
    ).fetchone()
    if row is None:
        return {"status": "no_payment", "valid_until": None, "last_payment": None}
    today = datetime.date.today().isoformat()
    status = "paid" if row["valid_until"] >= today else "overdue"
    return {"status": status, "valid_until": row["valid_until"], "last_payment": dict(row)}


def revenue_since(conn, since_date):
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM payments WHERE paid_on >= ?",
        (since_date,),
    ).fetchone()
    return row["total"]


def list_members_with_status(conn, status_filter=None):
    member_rows = conn.execute("SELECT * FROM members WHERE is_active = 1 ORDER BY first_name").fetchall()
    result = []
    for m in member_rows:
        status = get_status(conn, m["id"])
        entry = dict(m)
        entry.update(status)
        if status_filter is None or entry["status"] == status_filter:
            result.append(entry)
    return result


def upcoming_expirations(conn, within_days=7):
    cutoff = (datetime.date.today() + datetime.timedelta(days=within_days)).isoformat()
    entries = [
        entry
        for entry in list_members_with_status(conn, "paid")
        if entry["valid_until"] <= cutoff
    ]
    entries.sort(key=lambda entry: entry["valid_until"])
    return entries


def payment_history(conn, member_id, limit=None):
    sql = (
        "SELECT payments.*, membership_plans.name AS plan_name FROM payments "
        "JOIN membership_plans ON payments.plan_id = membership_plans.id "
        "WHERE member_id = ? ORDER BY paid_on DESC"
    )
    params = [member_id]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
