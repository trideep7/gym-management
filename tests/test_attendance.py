import datetime

from services import attendance, auth, members, payments


def setup_member_and_user(conn, name="Sam"):
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members.create_member(conn, {"first_name": name, "mobile": "111", "plan_id": plan_id})
    user_id = auth.create_user(conn, f"staff_{name}", "pw12345", "Staff One", "staff")
    return member_id, user_id


def test_sign_in_records_visit(conn):
    member_id, user_id = setup_member_and_user(conn)
    result = attendance.sign_in(conn, member_id, user_id)
    assert result["already_signed_in"] is False
    assert result["sign_in_time"]


def test_duplicate_sign_in_same_day_is_noop(conn):
    member_id, user_id = setup_member_and_user(conn)
    first = attendance.sign_in(conn, member_id, user_id)
    second = attendance.sign_in(conn, member_id, user_id)
    assert second["already_signed_in"] is True
    assert second["sign_in_time"] == first["sign_in_time"]
    count = conn.execute(
        "SELECT COUNT(*) AS c FROM attendance WHERE member_id = ?", (member_id,)
    ).fetchone()["c"]
    assert count == 1


def test_sign_in_on_different_days_creates_two_rows(conn):
    member_id, user_id = setup_member_and_user(conn)
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    attendance.sign_in(conn, member_id, user_id, when=yesterday)
    attendance.sign_in(conn, member_id, user_id)
    count = conn.execute(
        "SELECT COUNT(*) AS c FROM attendance WHERE member_id = ?", (member_id,)
    ).fetchone()["c"]
    assert count == 2


def test_list_today_returns_only_todays_signins(conn):
    member_id, user_id = setup_member_and_user(conn)
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    attendance.sign_in(conn, member_id, user_id, when=yesterday)
    today_rows = attendance.list_today(conn)
    assert today_rows == []
    attendance.sign_in(conn, member_id, user_id)
    assert len(attendance.list_today(conn)) == 1


def test_counts_by_day_aggregates_correctly(conn):
    member_a, user_id = setup_member_and_user(conn, "Alex")
    member_b, _ = setup_member_and_user(conn, "Bailey")
    attendance.sign_in(conn, member_a, user_id)
    attendance.sign_in(conn, member_b, user_id)
    today = datetime.date.today().isoformat()
    counts = attendance.counts_by_day(conn, today, today)
    assert counts == [{"date": today, "count": 2}]




def test_most_active_orders_by_checkin_count(conn):
    member_a, user_id = setup_member_and_user(conn, "Alex")
    member_b, _ = setup_member_and_user(conn, "Bailey")
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    attendance.sign_in(conn, member_a, user_id, when=yesterday)
    attendance.sign_in(conn, member_a, user_id)
    attendance.sign_in(conn, member_b, user_id)
    today = datetime.date.today().isoformat()
    yesterday_str = yesterday.date().isoformat()
    leaders = attendance.most_active(conn, yesterday_str, today)
    assert leaders[0]["member_id"] == member_a
    assert leaders[0]["checkins"] == 2
