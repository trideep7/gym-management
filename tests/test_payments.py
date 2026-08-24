import datetime

from services import auth, members, payments


def setup_member_and_user(conn):
    plan_id = payments.create_plan(conn, "Signup Default", 0.0, 30)
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "111", "plan_id": plan_id})
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


def test_status_is_overdue_after_plan_expires(conn):
    member_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    old_date = datetime.date.today() - datetime.timedelta(days=60)
    payments.mark_paid(conn, member_id, plan_id, user_id, paid_on=old_date)
    assert payments.get_status(conn, member_id)["status"] == "overdue"


def test_list_members_with_status_filters(conn):
    paid_id, user_id = setup_member_and_user(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    unpaid_id = members.create_member(conn, {"first_name": "Riley", "mobile": "222", "plan_id": plan_id})
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
    members.create_member(conn, {"first_name": "Sam", "mobile": "111", "plan_id": plan_id})

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
