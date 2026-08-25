import datetime

from services import attendance, auth, members, payments, reports


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


def test_most_active_members_delegates_to_attendance(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    attendance.sign_in(conn, member_id, user_id)
    today = datetime.date.today().isoformat()
    leaders = reports.most_active_members(conn, today, today)
    assert leaders[0]["member_id"] == member_id
    assert leaders[0]["checkins"] == 1
