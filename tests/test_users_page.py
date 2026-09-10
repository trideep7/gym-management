def login_as_admin(at):
    at.text_input(key="login_username").input("admin").run()
    at.text_input(key="login_password").input("password").run()
    at.button(key="login_button").click().run()
    return at


def test_admin_can_create_staff_user(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos"))
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/users.py")
    at.run()

    at.text_input(key="new_user_username").input("frontdesk").run()
    at.text_input(key="new_user_full_name").input("Front Desk").run()
    at.text_input(key="new_user_password").input("pw123456").run()
    at.button(key="FormSubmitter:new_user_form-Create User").click().run()

    assert not at.exception
    assert "created" in at.success[0].value.lower()
    # the Existing Users list (rendered above the form) must refresh in place
    assert any("Front Desk" in el.value for el in at.markdown)
    # Form-clearing (clear_on_submit=True) is verified separately via a real
    # browser (Playwright) — it resets via frontend widget state that AppTest
    # cannot observe through session_state, so it can't be asserted here.


def test_admin_can_reset_a_users_password(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test_reset.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos_reset"))
    import db as db_module
    from services import auth as auth_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    staff_id = auth_service.create_user(conn, "frontdesk3", "oldpassword", "Front Desk Three", "staff")
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/users.py")
    at.run()

    at.selectbox(key="reset_target").select(staff_id).run()
    at.text_input(key="reset_new_password").input("newpassword").run()
    at.button(key="FormSubmitter:reset_password_form-Reset Password").click().run()

    assert not at.exception
    assert "reset" in at.success[0].value.lower()

    import db as db_module

    check = db_module.get_connection()
    assert auth_service.authenticate(check, "frontdesk3", "newpassword") is not None
    check.close()


def test_staff_cannot_access_users_page(tmp_path, monkeypatch):
    # st.navigation already hides this page from staff (they can never
    # switch_page into it through app.py's own routing) — this test targets
    # the page's own defense-in-depth check directly, in case it is ever
    # reached some other way.
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test2.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos2"))
    import db as db_module

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../pages_/users.py")
    at.session_state["user"] = {"id": 999, "username": "staffer", "full_name": "Staff One", "role": "staff"}
    at.run()

    assert any("do not have access" in el.value.lower() for el in at.error)


def test_toggle_active_failure_shows_friendly_message_not_traceback(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test3.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos3"))
    import db as db_module
    from services import auth as auth_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    staff_id = auth_service.create_user(conn, "frontdesk2", "pw123456", "Front Desk Two", "staff")
    conn.close()

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(auth_service, "set_user_active", boom)

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/users.py")
    at.run()

    at.button(key=f"user_toggle_{staff_id}").click().run()

    assert not at.exception
    assert any("something went wrong" in el.value.lower() for el in at.error)
