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


def test_db_init_failure_shows_friendly_message_not_traceback(tmp_path, monkeypatch):
    # simulate a data folder the app can't write to (e.g. a permissions
    # problem on a fresh client machine) by making db.init_db blow up
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos"))
    import db as db_module

    def boom(conn):
        raise OSError("simulated permission denied")

    monkeypatch.setattr(db_module, "init_db", boom)

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()

    assert not at.exception
    assert any("couldn't start the app" in el.value.lower() for el in at.error)


def test_login_failure_shows_friendly_message_not_traceback(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test2.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos2"))
    from services import auth as auth_service

    def boom(conn, username, password):
        raise RuntimeError("simulated db error")

    monkeypatch.setattr(auth_service, "authenticate", boom)

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    at.text_input(key="login_username").input("admin").run()
    at.text_input(key="login_password").input("password").run()
    at.button(key="login_button").click().run()

    assert not at.exception
    assert any("something went wrong" in el.value.lower() for el in at.error)
