import pytest

import datetime

from services import auth, members, payments


def setup_member_and_user(conn):
    plan_id = payments.create_plan(conn, "Signup Default", 0.0, 30)
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    return member_id, user_id


def test_get_status_no_payment(conn):
    member_id, _ = setup_member_and_user(conn)
    status = payments.get_status(conn, member_id)
    assert status["status"] == "no_payment"
    assert status["valid_until"] is None


def test_mark_paid_then_status_is_paid(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date.today())
    status = payments.get_status(conn, member_id)
    assert status["status"] == "paid"
    assert status["valid_until"] == (datetime.date.today() + datetime.timedelta(days=30)).isoformat()


def test_mark_paid_adds_locker_fee_scaled_to_plan_duration(conn):
    plan_id = payments.create_plan(conn, "6 Months", 5000.0, 180)
    member_id = members.create_member(
        conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id, "has_locker": True}
    )
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    payments.mark_paid(conn, member_id, plan_id, user_id)
    history = payments.payment_history(conn, member_id)
    assert history[0]["amount"] == 5000.0 + 100 * 6


def test_mark_paid_adds_pt_fee_scaled_to_plan_duration(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    member_id = members.create_member(
        conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id, "has_pt": True}
    )
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    payments.mark_paid(conn, member_id, plan_id, user_id)
    history = payments.payment_history(conn, member_id)
    assert history[0]["amount"] == 1000.0 + 3000


def test_mark_paid_adds_both_locker_and_pt_fees(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    member_id = members.create_member(
        conn,
        {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id, "has_locker": True, "has_pt": True},
    )
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    payments.mark_paid(conn, member_id, plan_id, user_id)
    history = payments.payment_history(conn, member_id)
    assert history[0]["amount"] == 1000.0 + 100 + 3000


def test_mark_paid_without_locker_or_pt_charges_plan_amount_only(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id)
    history = payments.payment_history(conn, member_id)
    assert history[0]["amount"] == 1500.0


def test_quote_amount_matches_what_mark_paid_will_charge(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    member_id = members.create_member(
        conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id, "has_locker": True}
    )
    assert payments.quote_amount(conn, member_id, plan_id) == 1100.0


def test_status_is_overdue_after_plan_expires(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    old_date = datetime.date.today() - datetime.timedelta(days=60)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=old_date)
    assert payments.get_status(conn, member_id)["status"] == "overdue"


def test_list_members_with_status_filters(conn):
    paid_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    unpaid_id = members.create_member(conn, {"first_name": "Riley", "mobile": "9000000222", "plan_id": plan_id})
    payments.mark_paid(conn, paid_id, plan_id, user_id)

    paid_entries = payments.list_members_with_status(conn, "paid")
    no_payment_entries = payments.list_members_with_status(conn, "no_payment")

    assert {e["id"] for e in paid_entries} == {paid_id}
    assert {e["id"] for e in no_payment_entries} == {unpaid_id}


def test_payment_history_includes_plan_name(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id)
    history = payments.payment_history(conn, member_id)
    assert len(history) == 1
    assert history[0]["plan_name"] == "Monthly"


def test_set_plan_active_hides_from_default_list(conn):
    plan_id = payments.create_plan(conn, "Trial", 0.0, 7)
    payments.set_plan_active(conn, plan_id, False)
    active_names = {p["name"] for p in payments.list_plans(conn)}
    assert "Trial" not in active_names
    all_names = {p["name"] for p in payments.list_plans(conn, active_only=False)}
    assert "Trial" in all_names


def test_delete_plan_removes_unused_plan_completely(conn):
    plan_id = payments.create_plan(conn, "Trial", 0.0, 7)
    result = payments.delete_plan(conn, plan_id)
    assert result == "deleted"
    all_names = {p["name"] for p in payments.list_plans(conn, active_only=False)}
    assert "Trial" not in all_names


def test_delete_plan_deactivates_plan_assigned_to_member_with_no_payments(conn):
    plan_id = payments.create_plan(conn, "Trial", 0.0, 7)
    members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})

    result = payments.delete_plan(conn, plan_id)

    assert result == "deactivated"
    all_plans = {p["id"]: p for p in payments.list_plans(conn, active_only=False)}
    assert plan_id in all_plans
    assert all_plans[plan_id]["is_active"] == 0


def test_delete_plan_deactivates_plan_with_payment_history(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id)

    result = payments.delete_plan(conn, plan_id)

    assert result == "deactivated"
    all_plans = {p["id"]: p for p in payments.list_plans(conn, active_only=False)}
    assert plan_id in all_plans
    assert all_plans[plan_id]["is_active"] == 0
    # payment history must still resolve the plan name, i.e. the row survives
    history = payments.payment_history(conn, member_id)
    assert history[0]["plan_name"] == "Monthly"


def test_payment_history_respects_limit(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    base = datetime.date(2026, 1, 1)
    for i in range(8):
        payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=base + datetime.timedelta(days=i * 30))

    history = payments.payment_history(conn, member_id, limit=6)

    assert len(history) == 6
    # newest first — the 8th payment (i=7) was paid latest
    assert history[0]["paid_on"] == (base + datetime.timedelta(days=7 * 30)).isoformat()
    assert history[5]["paid_on"] == (base + datetime.timedelta(days=2 * 30)).isoformat()


def test_revenue_between_sums_amounts_within_the_range(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 10))
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 20))

    assert payments.revenue_between(conn, "2026-08-01", "2026-08-31") == 3000.0


def test_revenue_between_excludes_payments_dated_after_the_range(conn):
    # a member paying ahead for next month's cycle must not inflate this
    # month's total before that month arrives
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 15))
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 10, 1))

    assert payments.revenue_between(conn, "2026-08-01", "2026-08-31") == 1500.0


def test_revenue_between_excludes_payments_dated_before_the_range(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 7, 31))
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 15))

    assert payments.revenue_between(conn, "2026-08-01", "2026-08-31") == 1500.0


def test_payment_method_breakdown_splits_online_and_offline(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 10), payment_method="online")
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 12), payment_method="offline")
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 15), payment_method="offline")

    breakdown = payments.payment_method_breakdown(conn, "2026-08-01", "2026-08-31")

    assert breakdown == {"online": 1500.0, "offline": 3000.0, "unspecified": 0}


def test_payment_method_breakdown_buckets_missing_methods_as_unspecified(conn):
    # payments recorded before payment_method existed (or never given one)
    # must still show up somewhere, so the breakdown always reconciles
    # with the plain revenue total
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 10))

    breakdown = payments.payment_method_breakdown(conn, "2026-08-01", "2026-08-31")

    assert breakdown == {"online": 0, "offline": 0, "unspecified": 1500.0}


def test_payment_method_breakdown_excludes_payments_outside_the_range(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 7, 31), payment_method="online")
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 9, 1), payment_method="online")

    breakdown = payments.payment_method_breakdown(conn, "2026-08-01", "2026-08-31")

    assert breakdown == {"online": 0, "offline": 0, "unspecified": 0}


def test_revenue_by_day_groups_by_paid_on_date(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 10))
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 10))
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 12))

    by_day = payments.revenue_by_day(conn, "2026-08-01", "2026-08-31")

    assert by_day == [
        {"date": "2026-08-10", "total": 3000.0},
        {"date": "2026-08-12", "total": 1500.0},
    ]


def test_revenue_by_month_groups_and_orders_chronologically(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 6, 5))
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 3))
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=datetime.date(2026, 8, 20))

    by_month = payments.revenue_by_month(conn, "2026-06-01", "2026-08-31")

    assert by_month == [
        {"month": "2026-06", "total": 1500.0},
        {"month": "2026-08", "total": 3000.0},
    ]


def test_due_amounts_splits_active_and_inactive_members(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    members.create_member(conn, {"first_name": "ActiveUnpaid", "mobile": "9000000001", "plan_id": plan_id})
    inactive_unpaid = members.create_member(conn, {"first_name": "InactiveUnpaid", "mobile": "9000000002", "plan_id": plan_id})
    members.set_member_active(conn, inactive_unpaid, False)
    paid_member = members.create_member(conn, {"first_name": "Paid", "mobile": "9000000003", "plan_id": plan_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    payments.mark_paid(conn, paid_member, plan_id, user_id)

    due = payments.due_amounts(conn)

    assert due == {"active": 1500.0, "inactive": 1500.0}


def test_due_amounts_includes_locker_and_pt_surcharges(conn):
    # what's "due" must match what Mark Paid will actually charge, otherwise
    # the Reports due figures understate by the add-on fees
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    members.create_member(
        conn, {"first_name": "Plain", "mobile": "9000000001", "plan_id": plan_id}
    )
    members.create_member(
        conn, {"first_name": "Locker", "mobile": "9000000002", "plan_id": plan_id, "has_locker": True}
    )
    members.create_member(
        conn, {"first_name": "PT", "mobile": "9000000003", "plan_id": plan_id, "has_pt": True}
    )
    members.create_member(
        conn,
        {"first_name": "Both", "mobile": "9000000004", "plan_id": plan_id, "has_locker": True, "has_pt": True},
    )

    due = payments.due_amounts(conn)

    # 1000 + (1000+100) + (1000+3000) + (1000+100+3000)
    assert due["active"] == 1000.0 + 1100.0 + 4000.0 + 4100.0
    assert due["inactive"] == 0


def test_due_amounts_scales_surcharges_by_plan_duration(conn):
    plan_id = payments.create_plan(conn, "6 Months", 5000.0, 180)
    members.create_member(
        conn,
        {"first_name": "Sam", "mobile": "9000000001", "plan_id": plan_id, "has_locker": True, "has_pt": True},
    )

    due = payments.due_amounts(conn)

    assert due["active"] == 5000.0 + (100 * 6) + (3000 * 6)


def test_upcoming_expirations_includes_only_paid_members_expiring_within_window(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    today = datetime.date.today()

    expires_today = members.create_member(conn, {"first_name": "ExpiresToday", "mobile": "9000000001", "plan_id": plan_id})
    payments.mark_paid(conn, expires_today, plan_id, user_id, paid_on=today - datetime.timedelta(days=30))

    expires_in_3_days = members.create_member(conn, {"first_name": "ExpiresSoon", "mobile": "9000000002", "plan_id": plan_id})
    payments.mark_paid(conn, expires_in_3_days, plan_id, user_id, paid_on=today - datetime.timedelta(days=27))

    expires_in_10_days = members.create_member(conn, {"first_name": "ExpiresLater", "mobile": "9000000003", "plan_id": plan_id})
    payments.mark_paid(conn, expires_in_10_days, plan_id, user_id, paid_on=today - datetime.timedelta(days=20))

    overdue = members.create_member(conn, {"first_name": "Overdue", "mobile": "9000000004", "plan_id": plan_id})
    payments.mark_paid(conn, overdue, plan_id, user_id, paid_on=today - datetime.timedelta(days=35))

    no_payment = members.create_member(conn, {"first_name": "NoPay", "mobile": "9000000005", "plan_id": plan_id})

    upcoming = payments.upcoming_expirations(conn, within_days=7)

    ids = [entry["id"] for entry in upcoming]
    assert ids == [expires_today, expires_in_3_days]
    assert expires_in_10_days not in ids
    assert overdue not in ids
    assert no_payment not in ids


# --- billing periods: a member's cycle is anchored to their period,
# --- not to whichever day they happened to walk in with cash

def _cycle_member(conn, duration_days=30):
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, duration_days)
    member_id = members.create_member(
        conn, {"first_name": "Asha", "mobile": "9000000222", "plan_id": plan_id}
    )
    user_id = auth.create_user(conn, "cycle_staff", "pw12345", "Staff One", "staff")
    return member_id, plan_id, user_id


def _period(conn, member_id):
    row = conn.execute(
        "SELECT period_start, valid_until FROM payments WHERE member_id = ? "
        "ORDER BY id DESC LIMIT 1",
        (member_id,),
    ).fetchone()
    return row["period_start"], row["valid_until"]


def test_first_payment_starts_its_period_on_the_payment_date(conn):
    member_id, plan_id, user_id = _cycle_member(conn)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    assert _period(conn, member_id) == ("2026-01-15", "2026-02-14")


def test_renewal_paid_on_time_starts_the_day_after_the_last_period(conn):
    member_id, plan_id, user_id = _cycle_member(conn)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-02-14")
    assert _period(conn, member_id) == ("2026-02-15", "2026-03-17")


def test_renewal_paid_a_few_days_early_keeps_the_cycle(conn):
    member_id, plan_id, user_id = _cycle_member(conn)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-02-12")
    assert _period(conn, member_id) == ("2026-02-15", "2026-03-17")


def test_renewal_paid_a_few_days_late_keeps_the_cycle(conn):
    member_id, plan_id, user_id = _cycle_member(conn)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-02-17")
    assert _period(conn, member_id) == ("2026-02-15", "2026-03-17")


def test_renewal_paid_beyond_the_grace_window_restarts_from_the_payment_date(conn):
    member_id, plan_id, user_id = _cycle_member(conn)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-02-24")
    assert _period(conn, member_id) == ("2026-02-24", "2026-03-26")


def test_member_returning_months_later_restarts_from_the_payment_date(conn):
    member_id, plan_id, user_id = _cycle_member(conn)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-05-20")
    assert _period(conn, member_id) == ("2026-05-20", "2026-06-19")


def test_paying_far_in_advance_still_chains_rather_than_shortening_cover(conn):
    # prepaying a month early must never cut the member's own coverage
    # short -- only lateness past the grace window re-anchors
    member_id, plan_id, user_id = _cycle_member(conn)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-16")
    assert _period(conn, member_id) == ("2026-02-15", "2026-03-17")


def test_grace_window_is_read_from_settings(conn):
    from services import settings as settings_service

    member_id, plan_id, user_id = _cycle_member(conn)
    settings_service.set_renewal_grace_days(conn, 2)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    # five days late is inside the default 7-day window but outside this one
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-02-19")
    assert _period(conn, member_id) == ("2026-02-19", "2026-03-21")


def test_payment_date_is_recorded_separately_from_the_period(conn):
    member_id, plan_id, user_id = _cycle_member(conn)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-02-17")
    row = conn.execute(
        "SELECT paid_on, period_start FROM payments WHERE member_id = ? ORDER BY id DESC LIMIT 1",
        (member_id,),
    ).fetchone()
    assert row["paid_on"] == "2026-02-17"
    assert row["period_start"] == "2026-02-15"


# --- editing a plan -----------------------------------------------------

def test_update_plan_changes_name_amount_and_duration(conn):
    plan_id = payments.create_plan(conn, "Registration (3-Month)", 1500.0, 90)
    payments.update_plan(conn, plan_id, "Registration (1-Month)", 1500.0, 30)
    plan = next(p for p in payments.list_plans(conn) if p["id"] == plan_id)
    assert plan["name"] == "Registration (1-Month)"
    assert plan["amount"] == 1500.0
    assert plan["duration_days"] == 30


def test_update_plan_leaves_existing_payments_untouched(conn):
    # history is recorded per payment; shortening a plan must not
    # retroactively cut short a period somebody already paid for
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Registration", 1500.0, 90)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    before = payments.payment_history(conn, member_id)[0]

    payments.update_plan(conn, plan_id, "Registration", 1500.0, 30)

    after = payments.payment_history(conn, member_id)[0]
    assert after["paid_on"] == before["paid_on"]
    assert after["valid_until"] == before["valid_until"] == "2026-04-15"
    assert after["amount"] == before["amount"]


def test_update_plan_applies_the_new_duration_to_the_next_payment(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Registration", 1500.0, 90)
    payments.update_plan(conn, plan_id, "Registration", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    assert payments.payment_history(conn, member_id)[0]["valid_until"] == "2026-02-14"


def test_update_plan_rejects_a_blank_name(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    with pytest.raises(ValueError):
        payments.update_plan(conn, plan_id, "   ", 1000.0, 30)


def test_update_plan_rejects_a_duration_below_one_day(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    with pytest.raises(ValueError):
        payments.update_plan(conn, plan_id, "Monthly", 1000.0, 0)


def test_update_plan_rejects_a_negative_amount(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    with pytest.raises(ValueError):
        payments.update_plan(conn, plan_id, "Monthly", -1.0, 30)


def test_update_plan_rejects_an_unknown_plan(conn):
    with pytest.raises(ValueError):
        payments.update_plan(conn, 9999, "Ghost", 100.0, 30)


def test_update_plan_can_edit_a_deactivated_plan(conn):
    plan_id = payments.create_plan(conn, "Old Monthly", 1500.0, 30)
    payments.set_plan_active(conn, plan_id, False)
    payments.update_plan(conn, plan_id, "Old Monthly", 1200.0, 30)
    plan = next(p for p in payments.list_plans(conn, active_only=False) if p["id"] == plan_id)
    assert plan["amount"] == 1200.0
    assert plan["is_active"] == 0  # editing must not silently revive it


# --- payment method (online/offline) ------------------------------------

def test_mark_paid_records_the_payment_method(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, payment_method="online")
    history = payments.payment_history(conn, member_id)
    assert history[0]["payment_method"] == "online"


def test_mark_paid_without_a_payment_method_leaves_it_null(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id)
    history = payments.payment_history(conn, member_id)
    assert history[0]["payment_method"] is None


def test_mark_paid_rejects_an_unknown_payment_method(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    with pytest.raises(ValueError):
        payments.mark_paid(conn, member_id, plan_id, user_id, payment_method="cheque")


# --- editing a payment ---------------------------------------------------

def test_update_payment_changes_the_payment_method(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15", payment_method="offline")
    payment_id = payments.payment_history(conn, member_id)[0]["id"]

    payments.update_payment(conn, payment_id, payment_method="online", paid_on="2026-01-15", amount=1500.0)

    updated = payments.payment_history(conn, member_id)[0]
    assert updated["payment_method"] == "online"


def test_update_payment_rejects_an_unknown_payment_method(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payment_id = payments.payment_history(conn, member_id)[0]["id"]

    with pytest.raises(ValueError):
        payments.update_payment(conn, payment_id, payment_method="cheque", paid_on="2026-01-15", amount=1500.0)


def test_update_payment_rejects_an_unknown_payment_id(conn):
    with pytest.raises(ValueError):
        payments.update_payment(conn, 9999, payment_method="online", paid_on="2026-01-15", amount=1500.0)


def test_update_payment_leaves_the_period_untouched_when_the_date_is_unchanged(conn):
    # an early renewal chains its period_start away from paid_on -- fixing
    # just the payment method must not silently collapse that back to a
    # plain paid_on + duration_days period
    member_id, plan_id, user_id = _cycle_member(conn)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-02-12")  # chains to 02-15
    payment_id = payments.payment_history(conn, member_id)[0]["id"]
    before = payments.payment_history(conn, member_id)[0]

    payments.update_payment(
        conn, payment_id, payment_method="online", paid_on=before["paid_on"], amount=before["amount"]
    )

    after = payments.payment_history(conn, member_id)[0]
    assert after["period_start"] == before["period_start"] == "2026-02-15"
    assert after["valid_until"] == before["valid_until"] == "2026-03-17"


def test_update_payment_recalculates_its_own_period_when_the_date_changes(conn):
    # correcting the date is a standalone fix to this one payment's own
    # coverage -- it must not chain off (or ripple into) any other payment
    member_id, plan_id, user_id = _cycle_member(conn)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payment_id = payments.payment_history(conn, member_id)[0]["id"]

    payments.update_payment(conn, payment_id, payment_method="offline", paid_on="2026-01-20", amount=1500.0)

    updated = payments.payment_history(conn, member_id)[0]
    assert updated["paid_on"] == "2026-01-20"
    assert updated["period_start"] == "2026-01-20"
    assert updated["valid_until"] == "2026-02-19"


def test_update_payment_does_not_ripple_into_other_payments(conn):
    member_id, plan_id, user_id = _cycle_member(conn)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-02-14")
    history = payments.payment_history(conn, member_id)
    first_payment_id = history[1]["id"]  # oldest of the two
    second_before = history[0]

    payments.update_payment(conn, first_payment_id, payment_method="online", paid_on="2026-01-10", amount=1500.0)

    second_after = next(p for p in payments.payment_history(conn, member_id) if p["id"] == second_before["id"])
    assert second_after["period_start"] == second_before["period_start"]
    assert second_after["valid_until"] == second_before["valid_until"]


def test_update_payment_changes_the_amount(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payment_id = payments.payment_history(conn, member_id)[0]["id"]

    payments.update_payment(conn, payment_id, payment_method="offline", paid_on="2026-01-15", amount=1200.0)

    assert payments.payment_history(conn, member_id)[0]["amount"] == 1200.0


# --- editing a payment's plan ---------------------------------------------

def test_update_payment_without_plan_id_keeps_the_existing_plan(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payment_id = payments.payment_history(conn, member_id)[0]["id"]

    payments.update_payment(conn, payment_id, payment_method="offline", paid_on="2026-01-15", amount=1500.0)

    assert payments.payment_history(conn, member_id)[0]["plan_id"] == plan_id


def test_update_payment_can_change_the_plan(conn):
    member_id, user_id = setup_member_and_user(conn)
    monthly_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    registration_id = payments.create_plan(conn, "Registration (3-Month)", 4000.0, 90)
    payments.mark_paid(conn, member_id, monthly_id, user_id, paid_on="2026-01-15")
    payment_id = payments.payment_history(conn, member_id)[0]["id"]

    payments.update_payment(
        conn, payment_id, payment_method="offline", paid_on="2026-01-15", amount=4000.0, plan_id=registration_id
    )

    updated = payments.payment_history(conn, member_id)[0]
    assert updated["plan_id"] == registration_id
    assert updated["plan_name"] == "Registration (3-Month)"


def test_update_payment_changing_the_plan_recalculates_valid_until_from_its_duration(conn):
    # the coverage LENGTH must reflect the corrected plan even if the
    # start date (period_start) is left exactly where it was
    member_id, user_id = setup_member_and_user(conn)
    monthly_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    registration_id = payments.create_plan(conn, "Registration (3-Month)", 4000.0, 90)
    payments.mark_paid(conn, member_id, monthly_id, user_id, paid_on="2026-01-15")
    payment_id = payments.payment_history(conn, member_id)[0]["id"]

    payments.update_payment(
        conn, payment_id, payment_method="offline", paid_on="2026-01-15", amount=4000.0, plan_id=registration_id
    )

    updated = payments.payment_history(conn, member_id)[0]
    assert updated["period_start"] == "2026-01-15"  # anchor unchanged
    assert updated["valid_until"] == "2026-04-15"  # 90 days from the same anchor


def test_update_payment_rejects_an_unknown_plan_id(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payment_id = payments.payment_history(conn, member_id)[0]["id"]

    with pytest.raises(ValueError):
        payments.update_payment(
            conn, payment_id, payment_method="offline", paid_on="2026-01-15", amount=1500.0, plan_id=9999
        )


def test_update_payment_editing_the_plan_does_not_ripple_into_other_payments(conn):
    member_id, plan_id, user_id = _cycle_member(conn)
    registration_id = payments.create_plan(conn, "Registration (3-Month)", 4000.0, 90)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-02-14")
    history = payments.payment_history(conn, member_id)
    first_payment_id = history[1]["id"]  # oldest of the two
    second_before = history[0]

    payments.update_payment(
        conn, first_payment_id, payment_method="online", paid_on="2026-01-15", amount=4000.0,
        plan_id=registration_id,
    )

    second_after = next(p for p in payments.payment_history(conn, member_id) if p["id"] == second_before["id"])
    assert second_after["period_start"] == second_before["period_start"]
    assert second_after["valid_until"] == second_before["valid_until"]
    assert second_after["plan_id"] == second_before["plan_id"]


def test_update_payment_same_plan_and_date_leaves_period_untouched(conn):
    # re-selecting the payment's own current plan is a no-op for dates,
    # exactly like leaving paid_on unchanged already is
    member_id, plan_id, user_id = _cycle_member(conn)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-02-12")  # chains to 02-15
    before = payments.payment_history(conn, member_id)[0]

    payments.update_payment(
        conn, before["id"], payment_method="online", paid_on=before["paid_on"], amount=before["amount"],
        plan_id=before["plan_id"],
    )

    after = payments.payment_history(conn, member_id)[0]
    assert after["period_start"] == before["period_start"] == "2026-02-15"
    assert after["valid_until"] == before["valid_until"] == "2026-03-17"


def test_update_payment_rejects_a_negative_amount(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payment_id = payments.payment_history(conn, member_id)[0]["id"]

    with pytest.raises(ValueError):
        payments.update_payment(conn, payment_id, payment_method="offline", paid_on="2026-01-15", amount=-1.0)


# --- activity timestamps -------------------------------------------------

def test_mark_paid_sets_created_and_updated_timestamps(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id)
    payment = payments.payment_history(conn, member_id)[0]

    assert payment["created_at"] is not None
    assert payment["updated_at"] is not None
    assert payment["created_at"] == payment["updated_at"]
    datetime.datetime.fromisoformat(payment["created_at"])  # doesn't raise


def test_update_payment_bumps_updated_at_but_not_created_at(conn):
    import time

    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payment_id = payments.payment_history(conn, member_id)[0]["id"]
    original = payments.payment_history(conn, member_id)[0]

    time.sleep(0.01)
    payments.update_payment(conn, payment_id, payment_method="online", paid_on="2026-01-15", amount=1500.0)

    updated = payments.payment_history(conn, member_id)[0]
    assert updated["created_at"] == original["created_at"]
    assert updated["updated_at"] > original["updated_at"]


def test_mark_paid_attributes_updated_by_to_whoever_recorded_it(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id)

    assert payments.payment_history(conn, member_id)[0]["updated_by"] == user_id


def test_update_payment_attributes_updated_by_to_whoever_edited_it(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payment_id = payments.payment_history(conn, member_id)[0]["id"]
    editor_id = auth.create_user(conn, "editor", "pw12345", "Editor One", "staff")

    payments.update_payment(
        conn, payment_id, payment_method="online", paid_on="2026-01-15", amount=1500.0, updated_by=editor_id
    )

    updated = payments.payment_history(conn, member_id)[0]
    assert updated["updated_by"] == editor_id
    # recorded_by (who originally created it) must survive the edit
    assert updated["recorded_by"] == user_id


def test_update_payment_without_updated_by_leaves_it_unattributed(conn):
    # a programmatic edit that doesn't specify an actor is honestly
    # unattributed -- it must not silently keep crediting the original
    # recorder for someone else's later change
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payment_id = payments.payment_history(conn, member_id)[0]["id"]

    payments.update_payment(conn, payment_id, payment_method="online", paid_on="2026-01-15", amount=1500.0)

    assert payments.payment_history(conn, member_id)[0]["updated_by"] is None


def test_recent_payments_includes_member_and_plan_details(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id)
    today = datetime.date.today().isoformat()

    recent = payments.recent_payments(conn, today, today)

    assert len(recent) == 1
    assert recent[0]["member_first_name"] == "Sam"
    assert recent[0]["plan_name"] == "Monthly"
    assert recent[0]["amount"] == 1500.0


def test_recent_payments_includes_who_touched_it(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id)
    today = datetime.date.today().isoformat()

    recent = payments.recent_payments(conn, today, today)

    assert recent[0]["updated_by_role"] == "staff"
    assert recent[0]["updated_by_name"] == "Staff One"


def test_recent_payments_reports_no_name_when_unattributed(conn):
    # this is the "System" case the Recent Payments page falls back to
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    payment_id = payments.payment_history(conn, member_id)[0]["id"]
    payments.update_payment(conn, payment_id, payment_method="online", paid_on="2026-01-15", amount=1500.0)
    today = datetime.date.today().isoformat()

    recent = payments.recent_payments(conn, today, today)

    assert recent[0]["updated_by_name"] is None
    assert recent[0]["updated_by_role"] is None


def test_recent_payments_excludes_activity_outside_the_range(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id)

    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    two_days_ago = (datetime.date.today() - datetime.timedelta(days=2)).isoformat()

    assert payments.recent_payments(conn, two_days_ago, yesterday) == []


def test_recent_payments_orders_most_recently_updated_first(conn):
    import time

    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    first_id = payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-01-15")
    time.sleep(0.01)
    second_id = payments.mark_paid(conn, member_id, plan_id, user_id, paid_on="2026-02-15")
    time.sleep(0.01)
    # touching the older payment must move it back to the top
    payments.update_payment(conn, first_id, payment_method="online", paid_on="2026-01-15", amount=1500.0)

    today = datetime.date.today().isoformat()
    recent = payments.recent_payments(conn, today, today)

    assert [r["id"] for r in recent] == [first_id, second_id]


def test_recent_payments_excludes_rows_with_no_timestamp(conn):
    # a payment migrated in from before activity tracking existed has a
    # NULL updated_at -- it must never appear as if it just happened
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id)
    conn.execute("UPDATE payments SET created_at = NULL, updated_at = NULL")
    conn.commit()

    today = datetime.date.today().isoformat()
    assert payments.recent_payments(conn, today, today) == []


def test_delete_payment_removes_it(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    payments.mark_paid(conn, member_id, plan_id, user_id)
    payment_id = payments.payment_history(conn, member_id)[0]["id"]

    payments.delete_payment(conn, payment_id)

    assert payments.payment_history(conn, member_id) == []


def test_delete_payment_rejects_an_unknown_payment_id(conn):
    with pytest.raises(ValueError):
        payments.delete_payment(conn, 9999)
