import pytest


def login_as_admin(at):
    at.text_input(key="login_username").input("admin").run()
    at.text_input(key="login_password").input("password").run()
    at.button(key="login_button").click().run()
    return at


def test_dashboard_shows_metrics(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)

    assert not at.exception
    metric_values = [m.value for m in at.metric]
    assert "1" in metric_values
    assert any("No sign-ins yet today" in el.value for el in at.markdown)


def test_dashboard_shows_todays_signins(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test2.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos2"))
    import datetime

    import db as db_module
    from services import attendance, auth, members, payments

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members.create_member(conn, {"first_name": "Riley", "mobile": "9000000222", "plan_id": plan_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    # must be *today* — the Dashboard's list comes from attendance.list_today(),
    # so a hardcoded calendar date silently stops matching once the date rolls
    # over. Pin only the time-of-day, which is what the 02:32 PM assert checks.
    signed_in_at = datetime.datetime.combine(datetime.date.today(), datetime.time(14, 32, 0))
    attendance.sign_in(conn, member_id, user_id, when=signed_in_at)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)

    assert not at.exception
    markdown_values = [el.value for el in at.markdown]
    # Name, Phone, and Time as separate elements with a header row
    assert "**Name**" in markdown_values
    assert "**Phone**" in markdown_values
    assert "**Time**" in markdown_values
    assert any(el.value == "Riley" for el in at.markdown)
    assert any(el.value == "9000000222" for el in at.markdown)
    # 12-hour clock with AM/PM, not the raw 24-hour "14:32:00"
    assert any(el.value == "02:32 PM" for el in at.markdown)
    assert not any("14:32" in el.value for el in at.markdown)


def test_dashboard_signin_twice_same_day_warns_then_allows(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test3.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos3"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Riley", "mobile": "9000000222", "plan_id": plan_id})
    admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
    payments_service.mark_paid(conn, member_id, plan_id, admin_id)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)

    # the search box's key changes after each sign-in (forces a real reset
    # in the browser, since popping session_state alone doesn't visually
    # clear a widget that stays mounted across a rerun) — always grab the
    # current one positionally, since it's the only text_input on this page
    at.text_input[0].input("Riley").run()
    at.button(key=f"signin_{member_id}").click().run()
    assert not at.exception
    assert "signed in" in at.success[0].value.lower()
    # the search box must clear after a successful sign-in
    assert at.text_input[0].value == ""

    at.text_input[0].input("Riley").run()
    at.button(key=f"signin_{member_id}").click().run()
    # a same-day repeat now warns and asks for confirmation rather than
    # either blocking silently or signing in with no visibility at all
    assert not at.exception
    assert any("already signed in 1 time" in el.value.lower() for el in at.warning)
    assert at.button(key=f"confirm_signin_{member_id}")
    assert at.button(key=f"cancel_signin_{member_id}")
    # Clicking "Sign In Anyway" itself is verified separately via a real
    # browser (Playwright): AppTest has no structural model of st.dialog, and
    # a real dialog's button callback runs on a different thread than AppTest
    # drives — the click registers but the resulting attendance write never
    # lands within AppTest's simulation, even though it works in a real
    # browser (same gap documented for the unpaid/inactive confirm dialog).
    # Before this dialog even opened, the DB already has exactly one visit
    # (from the first sign-in above) — confirm that much here.
    conn = db_module.get_connection(str(tmp_path / "test3.db"))
    count = conn.execute("SELECT COUNT(*) AS c FROM attendance WHERE member_id = ?", (member_id,)).fetchone()["c"]
    assert count == 1
    conn.close()


def test_signin_failure_shows_friendly_message_not_traceback(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test4.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos4"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Riley", "mobile": "9000000222", "plan_id": plan_id})
    admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
    payments_service.mark_paid(conn, member_id, plan_id, admin_id)
    conn.close()

    from services import attendance as attendance_service

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(attendance_service, "sign_in", boom)

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)

    at.text_input[0].input("Riley").run()
    at.button(key=f"signin_{member_id}").click().run()

    assert not at.exception
    assert any("something went wrong" in el.value.lower() for el in at.error)


def test_signin_warns_before_signing_in_unpaid_member(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test5.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos5"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Riley", "mobile": "9000000222", "plan_id": plan_id})
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)

    at.text_input[0].input("Riley").run()
    at.button(key=f"signin_{member_id}").click().run()

    assert not at.exception
    # sign-in must not have happened yet — it's waiting on confirmation
    assert not at.success
    assert any("has not paid" in el.value.lower() for el in at.warning)
    assert at.button(key=f"confirm_signin_{member_id}")
    assert at.button(key=f"cancel_signin_{member_id}")
    # Clicking "Sign In Anyway" itself is verified separately via a real
    # browser (Playwright): AppTest has no structural model of st.dialog (no
    # `at.dialog` accessor, unlike `at.button`/`at.error`), and a real
    # Streamlit dialog's button callback runs on a different thread than
    # AppTest drives — the click registers but the resulting attendance
    # write never lands within AppTest's simulation, even though it works
    # correctly in a real browser.


def test_signin_cancel_does_not_sign_in_unpaid_member(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test6.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos6"))
    import db as db_module
    from services import attendance as attendance_service
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Riley", "mobile": "9000000222", "plan_id": plan_id})
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)

    at.text_input[0].input("Riley").run()
    at.button(key=f"signin_{member_id}").click().run()
    at.button(key=f"cancel_signin_{member_id}").click().run()

    assert not at.exception
    assert not at.success
    conn = db_module.get_connection(str(tmp_path / "test6.db"))
    count = conn.execute("SELECT COUNT(*) AS c FROM attendance WHERE member_id = ?", (member_id,)).fetchone()["c"]
    assert count == 0
    conn.close()


def test_signin_no_warning_for_paid_active_member(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test7.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos7"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Riley", "mobile": "9000000222", "plan_id": plan_id})
    admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
    payments_service.mark_paid(conn, member_id, plan_id, admin_id)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)

    at.text_input[0].input("Riley").run()
    at.button(key=f"signin_{member_id}").click().run()

    assert not at.exception
    assert not at.warning
    assert "signed in" in at.success[0].value.lower()


def test_signin_requires_phone_for_member_with_no_mobile_on_file(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test_nomobile.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos_nomobile"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Riley", "plan_id": plan_id})
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)

    at.text_input[0].input("Riley").run()

    assert not at.exception
    with pytest.raises(KeyError):
        at.button(key=f"signin_{member_id}")
    assert at.text_input(key=f"signin_phone_{member_id}")
    assert at.button(key=f"signin_save_phone_{member_id}")


def test_signin_save_phone_rejects_invalid_number(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test_badphone.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos_badphone"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Riley", "plan_id": plan_id})
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)

    at.text_input[0].input("Riley").run()
    at.text_input(key=f"signin_phone_{member_id}").input("123").run()
    at.button(key=f"signin_save_phone_{member_id}").click().run()

    assert not at.exception
    assert at.error
    assert not at.success

    conn = db_module.get_connection()
    assert members_service.get_member(conn, member_id)["mobile"] is None
    from services import attendance as attendance_service
    assert attendance_service.todays_signin_count(conn, member_id) == 0
    conn.close()


def test_signin_save_phone_rejects_blank_number(tmp_path, monkeypatch):
    # clicking Save with an empty box must not sign the member in with no
    # phone — that silently defeats the guard this whole branch exists for
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test_blankphone.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos_blankphone"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Riley", "plan_id": plan_id})
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)

    at.text_input[0].input("Riley").run()
    # leave signin_phone_ untouched (blank), then click Save
    at.button(key=f"signin_save_phone_{member_id}").click().run()

    assert not at.exception
    assert at.error
    assert not at.success

    conn = db_module.get_connection()
    # must stay NULL, not become an empty string
    assert members_service.get_member(conn, member_id)["mobile"] is None
    from services import attendance as attendance_service
    assert attendance_service.todays_signin_count(conn, member_id) == 0
    conn.close()


def test_signin_save_phone_then_signs_in_member(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test_savephone.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos_savephone"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Riley", "plan_id": plan_id})
    admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
    payments_service.mark_paid(conn, member_id, plan_id, admin_id)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)

    at.text_input[0].input("Riley").run()
    at.text_input(key=f"signin_phone_{member_id}").input("9000000333").run()
    at.button(key=f"signin_save_phone_{member_id}").click().run()

    assert not at.exception
    assert not at.error
    assert "signed in" in at.success[0].value.lower()

    conn = db_module.get_connection()
    assert members_service.get_member(conn, member_id)["mobile"] == "9000000333"
    from services import attendance as attendance_service
    assert attendance_service.todays_signin_count(conn, member_id) == 1
    conn.close()
