import datetime

from services import members as members_service
from services import payments as payments_service

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


def _resolve_paid_on(paid_on):
    if paid_on is None:
        return datetime.date.today().isoformat()
    if isinstance(paid_on, str):
        return paid_on
    return paid_on.isoformat()


def record_trainer_payment(conn, member_id, trainer_id, amount, trainer_share, recorded_by, paid_on=None):
    paid_on_str = _resolve_paid_on(paid_on)
    cursor = conn.execute(
        "INSERT INTO trainer_payments (member_id, trainer_id, amount, trainer_share, paid_on, recorded_by) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (member_id, trainer_id, amount, trainer_share, paid_on_str, recorded_by),
    )
    conn.commit()
    return cursor.lastrowid


def mark_paid_with_pt(conn, member_id, plan_id, recorded_by, paid_on=None):
    paid_on_str = _resolve_paid_on(paid_on)
    payment_id = payments_service.mark_paid(conn, member_id, plan_id, recorded_by, paid_on_str)

    member = members_service.get_member(conn, member_id)
    pt_charged = False
    if member and member["has_pt"] and member["trainer_id"]:
        plan = conn.execute("SELECT duration_days FROM membership_plans WHERE id = ?", (plan_id,)).fetchone()
        months = plan["duration_days"] / 30
        amount = payments_service.PT_MONTHLY_FEE * months
        trainer_share = PT_TRAINER_SHARE * months
        record_trainer_payment(conn, member_id, member["trainer_id"], amount, trainer_share, recorded_by, paid_on_str)
        pt_charged = True

    return {"payment_id": payment_id, "pt_charged": pt_charged}


def trainer_payouts(conn, start_date, end_date):
    rows = conn.execute(
        "SELECT trainers.id AS trainer_id, trainers.name AS trainer_name, "
        "COALESCE(SUM(trainer_payments.trainer_share), 0) AS amount_owed "
        "FROM trainers "
        "LEFT JOIN trainer_payments ON trainer_payments.trainer_id = trainers.id "
        "  AND trainer_payments.paid_on >= ? AND trainer_payments.paid_on <= ? "
        "WHERE trainers.is_active = 1 "
        "GROUP BY trainers.id ORDER BY trainers.name",
        (start_date, end_date),
    ).fetchall()
    return [dict(r) for r in rows]


def pt_summary(conn, start_date, end_date):
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total_fees, COALESCE(SUM(trainer_share), 0) AS total_trainer_share "
        "FROM trainer_payments WHERE paid_on >= ? AND paid_on <= ?",
        (start_date, end_date),
    ).fetchone()
    total_fees = row["total_fees"]
    total_trainer_share = row["total_trainer_share"]
    return {
        "total_fees": total_fees,
        "total_trainer_share": total_trainer_share,
        "total_gym_share": total_fees - total_trainer_share,
    }
