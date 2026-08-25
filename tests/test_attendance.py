import datetime

from services import attendance, auth, members, payments


def setup_member_and_user(conn, name="Sam"):
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members.create_member(conn, {"first_name": name, "mobile": "9000000111", "plan_id": plan_id})
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




def test_sign_in_handles_concurrent_insert_race(conn):
    # Simulates two people clicking "Sign In" for the same member at almost
    # the same instant: both pass the "does a row already exist?" check
    # before either has inserted, so the second INSERT hits the table's
    # UNIQUE(member_id, sign_in_date) constraint for real. sign_in() must
    # recover from that the same way it handles the normal duplicate case,
    # not let the IntegrityError escape.
    member_id, user_id = setup_member_and_user(conn)
    today = datetime.date.today().isoformat()

    # Insert the "winning" row directly, simulating the other request that
    # got there first.
    conn.execute(
        "INSERT INTO attendance (member_id, sign_in_date, sign_in_time, recorded_by) "
        "VALUES (?, ?, ?, ?)",
        (member_id, today, "09:00:00", user_id),
    )
    conn.commit()

    # Make sign_in()'s own pre-check believe no row exists yet (as if it ran
    # its SELECT before the other request's INSERT landed), so it falls
    # through to the INSERT and hits the real UNIQUE constraint. A real
    # sqlite3.Connection's `execute` attribute is read-only (can't be
    # monkeypatched directly), so wrap it in a thin forwarding proxy instead
    # — sign_in() only ever calls .execute()/.commit() on `conn`, so a
    # duck-typed stand-in works fine.
    class _EmptyResult:
        def fetchone(self):
            return None

    class FlakySelectConn:
        def __init__(self, real_conn):
            self._real = real_conn
            self._select_count = 0

        def execute(self, sql, params=()):
            if sql.startswith("SELECT sign_in_time FROM attendance") and self._select_count == 0:
                self._select_count += 1
                return _EmptyResult()
            return self._real.execute(sql, params)

        def commit(self):
            self._real.commit()

    result = attendance.sign_in(FlakySelectConn(conn), member_id, user_id)

    assert result == {"already_signed_in": True, "sign_in_time": "09:00:00"}
    count = conn.execute(
        "SELECT COUNT(*) AS c FROM attendance WHERE member_id = ?", (member_id,)
    ).fetchone()["c"]
    assert count == 1


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


def test_member_history_orders_newest_first_and_respects_limit(conn):
    member_id, user_id = setup_member_and_user(conn)
    base = datetime.datetime(2026, 1, 1, 9, 0, 0)
    for i in range(5):
        attendance.sign_in(conn, member_id, user_id, when=base + datetime.timedelta(days=i))

    history = attendance.member_history(conn, member_id, limit=3)

    assert len(history) == 3
    assert history[0]["sign_in_date"] == (base + datetime.timedelta(days=4)).date().isoformat()
    assert history[2]["sign_in_date"] == (base + datetime.timedelta(days=2)).date().isoformat()


def test_member_history_without_limit_returns_all(conn):
    member_id, user_id = setup_member_and_user(conn)
    base = datetime.datetime(2026, 1, 1, 9, 0, 0)
    for i in range(5):
        attendance.sign_in(conn, member_id, user_id, when=base + datetime.timedelta(days=i))

    assert len(attendance.member_history(conn, member_id)) == 5


def test_member_history_empty_for_member_with_no_signins(conn):
    member_id, _ = setup_member_and_user(conn)
    assert attendance.member_history(conn, member_id) == []
