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
