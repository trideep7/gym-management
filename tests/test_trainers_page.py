def login_as_admin(at):
    at.text_input(key="login_username").input("admin").run()
    at.text_input(key="login_password").input("password").run()
    at.button(key="login_button").click().run()
    return at


def open_trainers_page(tmp_path, monkeypatch, db_name="test.db", photos_name="photos"):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / db_name))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / photos_name))
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/trainers.py")
    at.run()
    return at


def test_add_trainer_shows_up_in_list(tmp_path, monkeypatch):
    at = open_trainers_page(tmp_path, monkeypatch)

    at.text_input(key="trainer_name").input("Alex").run()
    at.text_input(key="trainer_mobile").input("9000000001").run()
    at.text_input(key="trainer_time_slot").input("6-8 AM").run()
    at.button(key="add_trainer_button").click().run()

    assert not at.exception
    assert "added" in at.success[0].value.lower()
    assert any(el.value == "Alex" for el in at.markdown)


def test_edit_trainer_updates_list(tmp_path, monkeypatch):
    import db as db_module
    from services import trainers as trainers_service

    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test2.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos2"))
    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    trainer_id = trainers_service.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    conn.close()

    at = open_trainers_page(tmp_path, monkeypatch, "test2.db", "photos2")

    at.button(key=f"trainer_edit_{trainer_id}").click().run()
    at.text_input(key=f"edit_trainer_name_{trainer_id}").input("Alexander").run()
    at.button(key=f"save_trainer_{trainer_id}").click().run()

    assert not at.exception
    assert any(el.value == "Alexander" for el in at.markdown)
    assert not any(el.value == "Alex" for el in at.markdown)


def test_delete_trainer_removes_from_list(tmp_path, monkeypatch):
    import db as db_module
    from services import trainers as trainers_service

    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test3.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos3"))
    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    trainer_id = trainers_service.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    conn.close()

    at = open_trainers_page(tmp_path, monkeypatch, "test3.db", "photos3")

    at.button(key=f"trainer_delete_{trainer_id}").click().run()

    assert not at.exception
    assert "deleted" in at.success[0].value.lower()
    assert not any(el.value == "Alex" for el in at.markdown)
