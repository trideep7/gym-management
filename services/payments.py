import datetime

LOCKER_MONTHLY_FEE = 100
PT_MONTHLY_FEE = 3000


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


def _amount_for(plan, member):
    months = plan["duration_days"] / 30
    amount = plan["amount"]
    if member["has_locker"]:
        amount += LOCKER_MONTHLY_FEE * months
    if member["has_pt"]:
        amount += PT_MONTHLY_FEE * months
    return amount


def quote_amount(conn, member_id, plan_id):
    plan = conn.execute("SELECT * FROM membership_plans WHERE id = ?", (plan_id,)).fetchone()
    if plan is None:
        raise ValueError(f"No plan with id {plan_id}")
    member = conn.execute("SELECT has_locker, has_pt FROM members WHERE id = ?", (member_id,)).fetchone()
    if member is None:
        raise ValueError(f"No member with id {member_id}")
    return _amount_for(plan, member)


def mark_paid(conn, member_id, plan_id, recorded_by, paid_on=None):
    plan = conn.execute("SELECT * FROM membership_plans WHERE id = ?", (plan_id,)).fetchone()
    if plan is None:
        raise ValueError(f"No plan with id {plan_id}")
    member = conn.execute("SELECT has_locker, has_pt FROM members WHERE id = ?", (member_id,)).fetchone()
    if member is None:
        raise ValueError(f"No member with id {member_id}")

    if paid_on is None:
        paid_on_date = datetime.date.today()
    elif isinstance(paid_on, str):
        paid_on_date = datetime.date.fromisoformat(paid_on)
    else:
        paid_on_date = paid_on

    amount = _amount_for(plan, member)
    valid_until = paid_on_date + datetime.timedelta(days=plan["duration_days"])
    cursor = conn.execute(
        "INSERT INTO payments (member_id, plan_id, amount, paid_on, valid_until, recorded_by) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (member_id, plan_id, amount, paid_on_date.isoformat(), valid_until.isoformat(), recorded_by),
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


def revenue_by_day(conn, start_date, end_date):
    rows = conn.execute(
        "SELECT paid_on AS date, COALESCE(SUM(amount), 0) AS total FROM payments "
        "WHERE paid_on BETWEEN ? AND ? GROUP BY paid_on ORDER BY paid_on",
        (start_date, end_date),
    ).fetchall()
    return [dict(r) for r in rows]


def revenue_by_month(conn, start_date, end_date):
    rows = conn.execute(
        "SELECT strftime('%Y-%m', paid_on) AS month, COALESCE(SUM(amount), 0) AS total FROM payments "
        "WHERE paid_on >= ? AND paid_on <= ? GROUP BY month ORDER BY month",
        (start_date, end_date),
    ).fetchall()
    return [dict(r) for r in rows]


def list_members_with_status(conn, status_filter=None, active_only=True):
    sql = "SELECT * FROM members"
    if active_only:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY first_name"
    member_rows = conn.execute(sql).fetchall()
    result = []
    for m in member_rows:
        status = get_status(conn, m["id"])
        entry = dict(m)
        entry.update(status)
        if status_filter is None or entry["status"] == status_filter:
            result.append(entry)
    return result


def due_amounts(conn):
    # goes through _amount_for (not the bare plan amount) so what's reported
    # as due is exactly what Mark Paid will charge — locker/PT surcharges
    # included, scaled by plan duration
    plans = {row["id"]: dict(row) for row in conn.execute("SELECT * FROM membership_plans")}
    due = {"active": 0, "inactive": 0}
    for entry in list_members_with_status(conn, active_only=False):
        plan = plans.get(entry["plan_id"])
        if entry["status"] in ("overdue", "no_payment") and plan is not None:
            key = "active" if entry["is_active"] else "inactive"
            due[key] += _amount_for(plan, entry)
    return due


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
