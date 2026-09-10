import datetime

from services import attendance, auth, members, payments, reports, trainers


def test_signin_counts_delegates_to_attendance(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    attendance.sign_in(conn, member_id, user_id)
    today = datetime.date.today().isoformat()
    assert reports.signin_counts(conn, today, today) == [{"date": today, "count": 1}]


def test_payment_summary_counts_by_status(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    paid_id = members.create_member(conn, {"first_name": "Paid", "mobile": "9000000111", "plan_id": plan_id})
    overdue_id = members.create_member(conn, {"first_name": "Overdue", "mobile": "9000000222", "plan_id": plan_id})
    members.create_member(conn, {"first_name": "NoPay", "mobile": "9000000333", "plan_id": plan_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    payments.mark_paid(conn, paid_id, plan_id, user_id)
    payments.mark_paid(
        conn, overdue_id, plan_id, user_id, paid_on=datetime.date.today() - datetime.timedelta(days=60)
    )

    summary = reports.payment_summary(conn)

    assert summary["paid"] == 1
    assert summary["overdue"] == 1
    assert summary["no_payment"] == 1
    assert {m["id"] for m in summary["overdue_members"]} == {overdue_id}


def test_daily_revenue_fills_gaps_with_zero(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 10))

    by_day = reports.daily_revenue(conn, "2026-08-09", "2026-08-11")

    assert by_day == [
        {"date": "2026-08-09", "total": 0},
        {"date": "2026-08-10", "total": 1500.0},
        {"date": "2026-08-11", "total": 0},
    ]


def test_monthly_revenue_trend_returns_last_12_months_filled(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 15))
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2025, 12, 1))

    trend = reports.monthly_revenue_trend(conn, datetime.date(2026, 8, 26))

    assert len(trend) == 12
    assert trend[0]["month"] == "2025-09"
    assert trend[-1]["month"] == "2026-08"
    by_month = {row["month"]: row["total"] for row in trend}
    assert by_month["2026-08"] == 1500.0
    assert by_month["2025-12"] == 1500.0
    assert by_month["2025-09"] == 0


def test_overview_stats_returns_all_kpis(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    inactive_id = members.create_member(conn, {"first_name": "Gone", "mobile": "9000000222", "plan_id": plan_id})
    members.set_member_active(conn, inactive_id, False)
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    today = datetime.date(2026, 8, 26)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=today)

    stats = reports.overview_stats(conn, today)

    assert stats == {
        "revenue_this_month": 1500.0,
        "revenue_this_year": 1500.0,
        "active_members": 0,
        "payments_overdue": 0,
        "due_active": 0,
    }


def test_overview_stats_excludes_revenue_dated_after_the_current_month(conn):
    # a member paying ahead for a future cycle must not inflate this
    # month's (or this year's) revenue total before that month arrives --
    # this is exactly what "Revenue This Month" showing more than the
    # matching bar on the 12-month chart would mean
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    today = datetime.date(2026, 8, 26)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=today)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 9, 15))
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2027, 1, 10))

    stats = reports.overview_stats(conn, today)

    assert stats["revenue_this_month"] == 1500.0
    # the September payment is still within calendar year 2026, so it
    # counts toward the year total -- only the 2027 payment is excluded
    assert stats["revenue_this_year"] == 3000.0


def test_overview_stats_includes_revenue_dated_later_in_the_current_month(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    today = datetime.date(2026, 8, 5)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=today)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 26))  # later this month

    stats = reports.overview_stats(conn, today)

    assert stats["revenue_this_month"] == 3000.0


def test_payment_method_breakdown_this_month_splits_by_method(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    today = datetime.date(2026, 8, 26)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=today, payment_method="online")
    payments.mark_paid(
        conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 1), payment_method="offline"
    )
    # outside the month -- must not be counted
    payments.mark_paid(
        conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 9, 1), payment_method="online"
    )

    breakdown = reports.payment_method_breakdown_this_month(conn, today)

    assert breakdown == {"online": 1500.0, "offline": 1500.0, "unspecified": 0}


def test_due_summary_delegates_to_payments(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    inactive_id = members.create_member(conn, {"first_name": "Gone", "mobile": "9000000111", "plan_id": plan_id})
    members.set_member_active(conn, inactive_id, False)

    summary = reports.due_summary(conn)

    assert summary == {"active": 0, "inactive": 1500.0}


def test_most_active_members_delegates_to_attendance(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    attendance.sign_in(conn, member_id, user_id)
    today = datetime.date.today().isoformat()
    leaders = reports.most_active_members(conn, today, today)
    assert leaders[0]["member_id"] == member_id
    assert leaders[0]["checkins"] == 1


def test_pt_summary_delegates_to_trainers(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    trainer_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id, "trainer_id": trainer_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    trainers.record_trainer_payment(conn, member_id, trainer_id, 3000, 2000, user_id, paid_on=datetime.date(2026, 8, 5))

    summary = reports.pt_summary(conn, "2026-08-01", "2026-08-31")

    assert summary == {"total_fees": 3000, "total_trainer_share": 2000, "total_gym_share": 1000}


def test_trainer_payouts_delegates_to_trainers(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    trainer_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id, "trainer_id": trainer_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    trainers.record_trainer_payment(conn, member_id, trainer_id, 3000, 2000, user_id, paid_on=datetime.date(2026, 8, 5))

    payouts = reports.trainer_payouts(conn, "2026-08-01", "2026-08-31")

    assert payouts == [{"trainer_id": trainer_id, "trainer_name": "Alex", "amount_owed": 2000}]
