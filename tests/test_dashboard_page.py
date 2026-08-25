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
    import db as db_module
    from services import attendance, auth, members, payments

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members.create_member(conn, {"first_name": "Riley", "mobile": "9000000222", "plan_id": plan_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    attendance.sign_in(conn, member_id, user_id)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)

    assert not at.exception
    assert any("Riley" in el.value for el in at.markdown)


def test_dashboard_signin_and_duplicate_same_day(tmp_path, monkeypatch):
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
    assert any("already signed in" in el.value.lower() for el in at.info)


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
