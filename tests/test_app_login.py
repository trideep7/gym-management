def test_login_success(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos"))
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    at.text_input(key="login_username").input("admin").run()
    at.text_input(key="login_password").input("password").run()
    at.button(key="login_button").click().run()

    assert not at.exception
    assert at.session_state["user"]["username"] == "admin"
    assert at.session_state["user"]["role"] == "admin"


def test_login_failure_shows_error_and_no_session(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test2.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos2"))
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    at.text_input(key="login_username").input("admin").run()
    at.text_input(key="login_password").input("wrongpass").run()
    at.button(key="login_button").click().run()

    assert at.session_state["user"] is None
    assert len(at.error) == 1
