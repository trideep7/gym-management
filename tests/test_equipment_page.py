import pytest


def login_as_admin(at):
    at.text_input(key="login_username").input("admin").run()
    at.text_input(key="login_password").input("password").run()
    at.button(key="login_button").click().run()
    return at


def test_inventory_row_has_no_edit_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test3.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos3"))
    import db as db_module
    from services import equipment as equipment_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    equipment_id = equipment_service.create_equipment(conn, "Kettlebell", 4, "16kg set")
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/equipment.py")
    at.run()

    assert not at.exception
    with pytest.raises(KeyError):
        at.text_input(key=f"equip_edit_name_{equipment_id}")
    assert at.button(key=f"equip_delete_{equipment_id}")


def test_add_equipment_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos"))
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/equipment.py")
    at.run()

    at.text_input(key="equip_name").input("Treadmill").run()
    at.number_input(key="equip_quantity").set_value(3).run()
    at.button(key="FormSubmitter:new_equipment_form-Add Equipment").click().run()

    assert not at.exception
    assert "added" in at.success[0].value.lower()
    # the inventory list (rendered below the form) must show the new item immediately
    assert any("Treadmill" in el.value for el in at.markdown)
    # Form-clearing (clear_on_submit=True) is verified separately via a real
    # browser (Playwright) — it resets via frontend widget state that AppTest
    # cannot observe through session_state, so it can't be asserted here.


def test_delete_removes_item_immediately(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test2.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos2"))
    import db as db_module
    from services import equipment as equipment_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    equipment_id = equipment_service.create_equipment(conn, "Rowing Machine", 1)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/equipment.py")
    at.run()

    delete_button = at.button(key=f"equip_delete_{equipment_id}")
    assert delete_button.disabled is False

    delete_button.click().run()
    assert not at.exception
    with pytest.raises(KeyError):
        at.button(key=f"equip_delete_{equipment_id}")
