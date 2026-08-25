from services import auth, members, payments, reminders


def setup_member_and_user(conn):
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    return member_id, user_id


def test_log_reminder_returns_id(conn):
    member_id, user_id = setup_member_and_user(conn)
    reminder_id = reminders.log_reminder(conn, member_id, user_id)
    assert reminder_id is not None


def test_list_reminders_empty_for_member_with_none(conn):
    member_id, _ = setup_member_and_user(conn)
    assert reminders.list_reminders(conn, member_id) == []


def test_list_reminders_orders_newest_first_with_staff_name(conn):
    member_id, user_id = setup_member_and_user(conn)
    reminders.log_reminder(conn, member_id, user_id)
    reminders.log_reminder(conn, member_id, user_id)
    history = reminders.list_reminders(conn, member_id)
    assert len(history) == 2
    assert history[0]["sent_by_name"] == "Staff One"
    assert history[0]["sent_at"] >= history[1]["sent_at"]


def test_last_reminder_returns_none_when_no_reminders(conn):
    member_id, _ = setup_member_and_user(conn)
    assert reminders.last_reminder(conn, member_id) is None


def test_last_reminder_returns_most_recent(conn):
    member_id, user_id = setup_member_and_user(conn)
    reminders.log_reminder(conn, member_id, user_id)
    second_id = reminders.log_reminder(conn, member_id, user_id)
    last = reminders.last_reminder(conn, member_id)
    assert last["id"] == second_id
    assert last["sent_by_name"] == "Staff One"
