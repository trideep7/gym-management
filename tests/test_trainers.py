import datetime

from services import auth, members, payments, trainers


def setup_member_trainer_and_user(conn, has_pt=True, assign_trainer=True):
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    trainer_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    data = {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id, "has_pt": has_pt}
    if assign_trainer:
        data["trainer_id"] = trainer_id
    member_id = members.create_member(conn, data)
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    return member_id, trainer_id, plan_id, user_id


def test_create_and_list_trainers(conn):
    trainer_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    listed = trainers.list_trainers(conn)
    assert len(listed) == 1
    assert listed[0]["id"] == trainer_id
    assert listed[0]["name"] == "Alex"
    assert listed[0]["mobile"] == "9000000001"
    assert listed[0]["time_slot"] == "6-8 AM"
    assert listed[0]["is_active"] == 1


def test_list_trainers_orders_by_name(conn):
    trainers.create_trainer(conn, "Priya", "9000000002", "4-6 PM")
    trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    names = [t["name"] for t in trainers.list_trainers(conn)]
    assert names == ["Alex", "Priya"]


def test_update_trainer_changes_fields(conn):
    trainer_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    trainers.update_trainer(conn, trainer_id, "Alexander", "9000000009", "8-10 AM")
    updated = trainers.list_trainers(conn)[0]
    assert updated["name"] == "Alexander"
    assert updated["mobile"] == "9000000009"
    assert updated["time_slot"] == "8-10 AM"


def test_set_trainer_active_hides_from_default_list(conn):
    trainer_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    trainers.set_trainer_active(conn, trainer_id, False)
    active_names = {t["name"] for t in trainers.list_trainers(conn)}
    assert "Alex" not in active_names
    all_names = {t["name"] for t in trainers.list_trainers(conn, active_only=False)}
    assert "Alex" in all_names


def test_delete_trainer_removes_unused_trainer_completely(conn):
    trainer_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    result = trainers.delete_trainer(conn, trainer_id)
    assert result == "deleted"
    all_names = {t["name"] for t in trainers.list_trainers(conn, active_only=False)}
    assert "Alex" not in all_names


def test_delete_trainer_deactivates_trainer_assigned_to_a_member(conn):
    trainer_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id, "trainer_id": trainer_id})

    result = trainers.delete_trainer(conn, trainer_id)

    assert result == "deactivated"
    all_trainers = {t["id"]: t for t in trainers.list_trainers(conn, active_only=False)}
    assert trainer_id in all_trainers
    assert all_trainers[trainer_id]["is_active"] == 0


def test_delete_trainer_deactivates_trainer_with_payment_history(conn):
    trainer_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    trainers.record_trainer_payment(conn, member_id, trainer_id, 3000, 2000, user_id)

    result = trainers.delete_trainer(conn, trainer_id)

    assert result == "deactivated"


def test_record_trainer_payment_persists_given_amounts(conn):
    member_id, trainer_id, _, user_id = setup_member_trainer_and_user(conn)

    trainer_payment_id = trainers.record_trainer_payment(
        conn, member_id, trainer_id, 3000, 2000, user_id, paid_on=datetime.date(2026, 8, 1)
    )

    row = conn.execute("SELECT * FROM trainer_payments WHERE id = ?", (trainer_payment_id,)).fetchone()
    assert row["amount"] == 3000
    assert row["trainer_share"] == 2000
    assert row["paid_on"] == "2026-08-01"
    assert row["member_id"] == member_id
    assert row["trainer_id"] == trainer_id


def test_mark_paid_with_pt_logs_payout_when_has_pt_and_trainer_assigned(conn):
    member_id, trainer_id, plan_id, user_id = setup_member_trainer_and_user(conn, has_pt=True, assign_trainer=True)

    result = trainers.mark_paid_with_pt(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 1))

    assert result["pt_charged"] is True
    payment_count = conn.execute("SELECT COUNT(*) AS c FROM payments WHERE member_id = ?", (member_id,)).fetchone()["c"]
    assert payment_count == 1
    tp = conn.execute("SELECT * FROM trainer_payments WHERE member_id = ?", (member_id,)).fetchone()
    assert tp["amount"] == 3000
    assert tp["trainer_share"] == 2000
    assert tp["paid_on"] == "2026-08-01"
    # the member's own payment already includes the PT surcharge via has_pt
    payment = conn.execute("SELECT amount FROM payments WHERE member_id = ?", (member_id,)).fetchone()
    assert payment["amount"] == 1000.0 + 3000


def test_mark_paid_with_pt_scales_payout_by_plan_duration(conn):
    trainer_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    plan_id = payments.create_plan(conn, "6 Months", 5000.0, 180)
    member_id = members.create_member(
        conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id, "has_pt": True, "trainer_id": trainer_id}
    )
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")

    trainers.mark_paid_with_pt(conn, member_id, plan_id, user_id)

    tp = conn.execute("SELECT * FROM trainer_payments WHERE member_id = ?", (member_id,)).fetchone()
    assert tp["amount"] == 3000 * 6
    assert tp["trainer_share"] == 2000 * 6


def test_mark_paid_with_pt_no_payout_without_has_pt(conn):
    member_id, trainer_id, plan_id, user_id = setup_member_trainer_and_user(conn, has_pt=False, assign_trainer=True)

    result = trainers.mark_paid_with_pt(conn, member_id, plan_id, user_id)

    assert result["pt_charged"] is False
    count = conn.execute("SELECT COUNT(*) AS c FROM trainer_payments WHERE member_id = ?", (member_id,)).fetchone()["c"]
    assert count == 0


def test_mark_paid_with_pt_still_charges_when_no_trainer_assigned(conn):
    # deliberate behaviour change: previously this logged nothing, which meant
    # the gym collected the PT fee (charged off has_pt by _amount_for) while
    # Reports showed 0. The payout is now recorded unattributed instead.
    member_id, _, plan_id, user_id = setup_member_trainer_and_user(conn, has_pt=True, assign_trainer=False)

    result = trainers.mark_paid_with_pt(conn, member_id, plan_id, user_id)

    assert result["pt_charged"] is True
    count = conn.execute("SELECT COUNT(*) AS c FROM trainer_payments WHERE member_id = ?", (member_id,)).fetchone()["c"]
    assert count == 1


def test_mark_paid_with_pt_stops_logging_after_has_pt_turned_off(conn):
    member_id, trainer_id, plan_id, user_id = setup_member_trainer_and_user(conn, has_pt=True, assign_trainer=True)

    first = trainers.mark_paid_with_pt(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 1))
    assert first["pt_charged"] is True

    member = members.get_member(conn, member_id)
    members.update_member(conn, member_id, {**member, "has_pt": False})

    second = trainers.mark_paid_with_pt(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 9, 1))

    assert second["pt_charged"] is False
    count = conn.execute("SELECT COUNT(*) AS c FROM trainer_payments WHERE member_id = ?", (member_id,)).fetchone()["c"]
    assert count == 1  # only the first month's payout


def test_trainer_payouts_sums_per_trainer_in_range(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    alex_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    trainers.create_trainer(conn, "Priya", "9000000002", "4-6 PM")
    member_a = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id, "trainer_id": alex_id})
    member_b = members.create_member(conn, {"first_name": "Riley", "mobile": "9000000222", "plan_id": plan_id, "trainer_id": alex_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")

    trainers.record_trainer_payment(conn, member_a, alex_id, 3000, 2000, user_id, paid_on=datetime.date(2026, 8, 5))
    trainers.record_trainer_payment(conn, member_b, alex_id, 3000, 2000, user_id, paid_on=datetime.date(2026, 8, 10))
    trainers.record_trainer_payment(conn, member_a, alex_id, 3000, 2000, user_id, paid_on=datetime.date(2026, 7, 1))  # out of range

    payouts = trainers.trainer_payouts(conn, "2026-08-01", "2026-08-31")

    by_name = {p["trainer_name"]: p["amount_owed"] for p in payouts}
    assert by_name["Alex"] == 4000
    assert by_name["Priya"] == 0


def test_pt_summary_totals_across_all_trainers(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    trainer_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id, "trainer_id": trainer_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    trainers.record_trainer_payment(conn, member_id, trainer_id, 3000, 2000, user_id, paid_on=datetime.date(2026, 8, 5))

    summary = trainers.pt_summary(conn, "2026-08-01", "2026-08-31")

    assert summary == {"total_fees": 3000, "total_trainer_share": 2000, "total_gym_share": 1000}


def test_mark_paid_with_pt_logs_unattributed_payout_when_no_trainer_assigned(conn):
    # The gym collects the PT fee off has_pt alone (services/payments._amount_for),
    # so the payout has to be recorded even when nobody is assigned yet —
    # otherwise the money is charged but reported as zero.
    member_id, _, plan_id, user_id = setup_member_trainer_and_user(conn, has_pt=True, assign_trainer=False)

    result = trainers.mark_paid_with_pt(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 1))

    assert result["pt_charged"] is True
    tp = conn.execute("SELECT * FROM trainer_payments WHERE member_id = ?", (member_id,)).fetchone()
    assert tp["trainer_id"] is None
    assert tp["amount"] == 3000
    assert tp["trainer_share"] == 2000


def test_pt_summary_includes_unattributed_payouts(conn):
    member_id, _, plan_id, user_id = setup_member_trainer_and_user(conn, has_pt=True, assign_trainer=False)
    trainers.mark_paid_with_pt(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 5))

    summary = trainers.pt_summary(conn, "2026-08-01", "2026-08-31")

    assert summary == {"total_fees": 3000, "total_trainer_share": 2000, "total_gym_share": 1000}


def test_trainer_payouts_reports_unassigned_bucket(conn):
    member_id, trainer_id, plan_id, user_id = setup_member_trainer_and_user(conn, has_pt=True, assign_trainer=True)
    trainers.mark_paid_with_pt(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 5))

    other = members.create_member(
        conn, {"first_name": "Riley", "mobile": "9000000222", "plan_id": plan_id, "has_pt": True}
    )
    trainers.mark_paid_with_pt(conn, other, plan_id, user_id, paid_on=datetime.date(2026, 8, 6))

    payouts = trainers.trainer_payouts(conn, "2026-08-01", "2026-08-31")

    named = {p["trainer_name"]: p["amount_owed"] for p in payouts if p["trainer_id"] is not None}
    unassigned = [p for p in payouts if p["trainer_id"] is None]
    assert named["Alex"] == 2000
    assert len(unassigned) == 1
    assert unassigned[0]["amount_owed"] == 2000
    assert unassigned[0]["trainer_name"] is None


def test_trainer_payouts_omits_unassigned_bucket_when_all_attributed(conn):
    member_id, trainer_id, plan_id, user_id = setup_member_trainer_and_user(conn, has_pt=True, assign_trainer=True)
    trainers.mark_paid_with_pt(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 5))

    payouts = trainers.trainer_payouts(conn, "2026-08-01", "2026-08-31")

    assert all(p["trainer_id"] is not None for p in payouts)
