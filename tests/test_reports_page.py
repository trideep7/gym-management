def login_as_admin(at):
    at.text_input(key="login_username").input("admin").run()
    at.text_input(key="login_password").input("password").run()
    at.button(key="login_button").click().run()
    return at


def test_reports_page_renders_without_error(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos"))
    import db as db_module
    from services import attendance, auth, members, payments

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "111", "plan_id": plan_id})
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    attendance.sign_in(conn, member_id, user_id)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/reports.py")
    at.run()
    at.button[0].click().run()

    assert not at.exception
    metric_values = [m.value for m in at.metric]
    assert "0" in metric_values
