def login_as_admin(at):
    at.text_input(key="login_username").input("admin").run()
    at.text_input(key="login_password").input("password").run()
    at.button(key="login_button").click().run()
    return at


def _fresh_app(tmp_path, monkeypatch, name):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / f"{name}.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / f"photos_{name}"))
    import db as db_module

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    return conn


def _seed_locker_holders(conn, count):
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    for i in range(count):
        members_service.create_member(
            conn,
            {"first_name": f"Holder{i}", "mobile": f"90000002{i:02d}",
             "plan_id": plan_id, "has_locker": True},
        )
    return plan_id


def test_gym_settings_saves_the_locker_total(tmp_path, monkeypatch):
    conn = _fresh_app(tmp_path, monkeypatch, "gym1")
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/settings_gym.py")
    at.run()

    at.number_input(key="settings_locker_count").set_value(40).run()
    at.button(key="settings_gym_save").click().run()

    assert not at.exception
    import db as db_module
    from services import settings as settings_service

    check = db_module.get_connection()
    assert settings_service.get_locker_count(check) == 40
    check.close()


def test_gym_settings_reports_how_many_lockers_are_in_use(tmp_path, monkeypatch):
    conn = _fresh_app(tmp_path, monkeypatch, "gym2")
    _seed_locker_holders(conn, 3)
    from services import settings as settings_service

    settings_service.set_locker_count(conn, 10)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/settings_gym.py")
    at.run()

    assert not at.exception
    assert any("3 of 10" in el.value for el in at.caption)


def test_gym_settings_refuses_a_total_below_the_lockers_already_in_use(tmp_path, monkeypatch):
    conn = _fresh_app(tmp_path, monkeypatch, "gym3")
    _seed_locker_holders(conn, 5)
    from services import settings as settings_service

    settings_service.set_locker_count(conn, 10)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/settings_gym.py")
    at.run()

    at.number_input(key="settings_locker_count").set_value(2).run()
    at.button(key="settings_gym_save").click().run()

    assert not at.exception
    assert at.error
    import db as db_module

    check = db_module.get_connection()
    assert settings_service.get_locker_count(check) == 10  # unchanged
    check.close()


def test_gym_settings_saves_the_renewal_grace_window(tmp_path, monkeypatch):
    conn = _fresh_app(tmp_path, monkeypatch, "gym4")
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/settings_gym.py")
    at.run()

    at.number_input(key="settings_grace_days").set_value(3).run()
    at.button(key="settings_gym_save").click().run()

    assert not at.exception
    import db as db_module
    from services import settings as settings_service

    check = db_module.get_connection()
    assert settings_service.get_renewal_grace_days(check) == 3
    check.close()


def test_membership_plans_page_lists_and_adds_plans(tmp_path, monkeypatch):
    conn = _fresh_app(tmp_path, monkeypatch, "plans1")
    from services import payments as payments_service

    payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/settings_plans.py")
    at.run()

    assert not at.exception
    assert any("Monthly" in el.value for el in at.markdown)

    at.text_input(key="plan_name").input("Quarterly").run()
    at.number_input(key="plan_amount").set_value(4000.0).run()
    at.number_input(key="plan_duration").set_value(90).run()
    at.button(key="add_plan_button").click().run()

    assert not at.exception
    import db as db_module

    check = db_module.get_connection()
    assert any(p["name"] == "Quarterly" for p in payments_service.list_plans(check))
    check.close()


def test_delete_unused_plan_removes_it_from_the_list(tmp_path, monkeypatch):
    conn = _fresh_app(tmp_path, monkeypatch, "plans2")
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Trial", 0.0, 7)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/settings_plans.py")
    at.run()

    at.button(key=f"plan_delete_{plan_id}").click().run()

    assert not at.exception
    assert "deleted" in at.success[0].value.lower()
    assert not any("Trial" in el.value for el in at.markdown)


def test_delete_plan_assigned_to_a_member_deactivates_instead(tmp_path, monkeypatch):
    conn = _fresh_app(tmp_path, monkeypatch, "plans3")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Trial", 0.0, 7)
    members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/settings_plans.py")
    at.run()

    at.button(key=f"plan_delete_{plan_id}").click().run()

    assert not at.exception
    assert "deactivated" in at.success[0].value.lower()
    assert "Trial" in at.success[0].value
    assert not any(el.value == "Trial" for el in at.markdown)


def test_delete_plan_with_payment_history_deactivates_instead(tmp_path, monkeypatch):
    conn = _fresh_app(tmp_path, monkeypatch, "plans4")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
    payments_service.mark_paid(conn, member_id, plan_id, admin_id)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/settings_plans.py")
    at.run()

    at.button(key=f"plan_delete_{plan_id}").click().run()

    assert not at.exception
    assert "deactivated" in at.success[0].value.lower()
    assert "Monthly" in at.success[0].value
    assert not any(el.value == "Monthly" for el in at.markdown)
