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
    at.selectbox(key="trainer_time_slot").select("8:00 AM - 10:00 AM").run()
    at.button(key="add_trainer_button").click().run()

    assert not at.exception
    assert "added" in at.success[0].value.lower()
    assert any(el.value == "Alex" for el in at.markdown)
    assert any(el.value == "8:00 AM - 10:00 AM" for el in at.markdown)


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


def test_trainer_time_slot_offers_the_same_options_as_the_member_form(tmp_path, monkeypatch):
    import db as db_module
    from services import time_slots as time_slots_service
    from utils import time_slots

    at = open_trainers_page(tmp_path, monkeypatch, "slots1.db", "photos_slots1")

    assert not at.exception
    check = db_module.get_connection()
    expected_labels = [s["label"] for s in time_slots_service.list_time_slots(check)]
    check.close()
    assert at.selectbox(key="trainer_time_slot").options == [time_slots.NOT_SET] + expected_labels


def test_adding_a_trainer_without_a_slot_stores_no_slot(tmp_path, monkeypatch):
    import db as db_module
    from services import trainers as trainers_service

    at = open_trainers_page(tmp_path, monkeypatch, "slots2.db", "photos_slots2")

    at.text_input(key="trainer_name").input("Alex").run()
    at.button(key="add_trainer_button").click().run()

    assert not at.exception
    conn = db_module.get_connection()
    assert trainers_service.list_trainers(conn)[0]["time_slot"] is None
    conn.close()


def test_editing_a_trainers_slot_uses_the_dropdown(tmp_path, monkeypatch):
    import db as db_module
    from services import trainers as trainers_service

    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "slots3.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos_slots3"))
    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    trainer_id = trainers_service.create_trainer(conn, "Alex", "9000000001", "6:00 AM - 8:00 AM")
    conn.close()

    at = open_trainers_page(tmp_path, monkeypatch, "slots3.db", "photos_slots3")
    at.button(key=f"trainer_edit_{trainer_id}").click().run()

    slot = at.selectbox(key=f"edit_trainer_time_slot_{trainer_id}")
    assert slot.value == "6:00 AM - 8:00 AM"

    slot.select("4:00 PM - 6:00 PM").run()
    at.button(key=f"save_trainer_{trainer_id}").click().run()

    assert not at.exception
    check = db_module.get_connection()
    assert trainers_service.list_trainers(check)[0]["time_slot"] == "4:00 PM - 6:00 PM"
    check.close()


def test_an_unrecognised_stored_slot_is_kept_not_silently_rewritten(tmp_path, monkeypatch):
    # a legacy free-text value must survive an unrelated edit
    import db as db_module
    from services import trainers as trainers_service

    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "slots4.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos_slots4"))
    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    trainer_id = trainers_service.create_trainer(conn, "Joe", "9000000002", "8am-10am")
    conn.close()

    at = open_trainers_page(tmp_path, monkeypatch, "slots4.db", "photos_slots4")
    at.button(key=f"trainer_edit_{trainer_id}").click().run()

    assert at.selectbox(key=f"edit_trainer_time_slot_{trainer_id}").value == "8am-10am"

    at.text_input(key=f"edit_trainer_name_{trainer_id}").input("Joseph").run()
    at.button(key=f"save_trainer_{trainer_id}").click().run()

    assert not at.exception
    check = db_module.get_connection()
    trainer = trainers_service.list_trainers(check)[0]
    assert trainer["name"] == "Joseph"
    assert trainer["time_slot"] == "8am-10am"
    check.close()
