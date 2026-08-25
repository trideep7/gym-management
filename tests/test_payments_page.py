import pytest


def login_as_admin(at):
    at.text_input(key="login_username").input("admin").run()
    at.text_input(key="login_password").input("password").run()
    at.button(key="login_button").click().run()
    return at


def test_mark_payment_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/payments.py")
    at.run()

    at.button(key=f"mark_paid_{member_id}").click().run()

    assert not at.exception
    assert "paid" in at.success[0].value.lower()
    # the status row itself must refresh in place, not just show the flash message
    assert any("Paid" == el.value for el in at.markdown)
    assert not any(el.value == "No Payment" for el in at.markdown)


def test_status_list_shows_last_paid_date(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test10.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos10"))
    import datetime

    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    paid_id = members_service.create_member(conn, {"first_name": "Riley", "mobile": "9000000555", "plan_id": plan_id})
    unpaid_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000556", "plan_id": plan_id})
    admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
    paid_on = datetime.date.today() - datetime.timedelta(days=5)
    payments_service.mark_paid(conn, paid_id, plan_id, admin_id, paid_on=paid_on)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/payments.py")
    at.run()

    assert not at.exception
    assert any("**Last Paid**" == el.value for el in at.markdown)
    assert any(el.value == paid_on.strftime("%d-%b-%Y") for el in at.markdown)


def test_status_list_displays_members_own_plan_as_text_not_selectbox(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test7.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos7"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    payments_service.create_plan(conn, "6 Months", 5000.0, 180)
    monthly_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(
        conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": monthly_id}
    )
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/payments.py")
    at.run()

    assert not at.exception
    # plan is now plain text, not a selectbox — nothing to choose here
    with pytest.raises(KeyError):
        at.selectbox(key=f"plan_select_{member_id}")
    assert any(el.value == "Monthly" for el in at.markdown)
    # header row present
    assert any("**Plan**" == el.value for el in at.markdown)
    assert any("**Mark Paid**" == el.value for el in at.markdown)


def test_mark_paid_disabled_when_member_has_no_plan(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test9.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos9"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    # simulate a legacy member with no plan assigned (pre-migration state)
    conn.execute("UPDATE members SET plan_id = NULL WHERE id = ?", (member_id,))
    conn.commit()
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/payments.py")
    at.run()

    assert not at.exception
    assert any(el.value == "No plan assigned" for el in at.markdown)
    assert at.button(key=f"mark_paid_{member_id}").disabled is True


def test_add_plan_flow_refreshes_plan_list(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test3.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos3"))
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/payments.py")
    at.run()

    at.text_input(key="plan_name").input("Quarterly").run()
    at.button(key="FormSubmitter:new_plan_form-Add Plan").click().run()

    assert not at.exception
    assert "added" in at.success[0].value.lower()
    assert any("Quarterly" in el.value for el in at.markdown)


def test_delete_unused_plan_removes_it_from_list(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test4.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos4"))
    import db as db_module
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Trial", 0.0, 7)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/payments.py")
    at.run()

    at.button(key=f"plan_delete_{plan_id}").click().run()

    assert not at.exception
    assert "deleted" in at.success[0].value.lower()
    assert not any("Trial" in el.value for el in at.markdown)


def test_delete_plan_assigned_to_member_deactivates_instead(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test8.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos8"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Trial", 0.0, 7)
    members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/payments.py")
    at.run()

    at.button(key=f"plan_delete_{plan_id}").click().run()

    assert not at.exception
    assert "deactivated" in at.success[0].value.lower()
    assert "Trial" in at.success[0].value
    # gone from the Manage Plans list, but still correctly shown as Sam's
    # assigned plan in the Member Status list — exactly one mention left
    assert sum(1 for el in at.markdown if el.value == "Trial") == 1


def test_delete_plan_in_use_deactivates_instead(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test5.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos5"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
    payments_service.mark_paid(conn, member_id, plan_id, admin_id)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/payments.py")
    at.run()

    at.button(key=f"plan_delete_{plan_id}").click().run()

    assert not at.exception
    assert "deactivated" in at.success[0].value.lower()
    assert "Monthly" in at.success[0].value
    # gone from the Manage Plans list, but still correctly shown as Sam's
    # assigned plan in the Member Status list — exactly one mention left
    assert sum(1 for el in at.markdown if el.value == "Monthly") == 1


def test_mark_paid_failure_shows_friendly_message_not_traceback(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test10.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos10"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000555", "plan_id": plan_id})
    conn.close()

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(payments_service, "mark_paid", boom)

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/payments.py")
    at.run()

    at.button(key=f"mark_paid_{member_id}").click().run()

    assert not at.exception
    assert any("something went wrong" in el.value.lower() for el in at.error)


def test_reminder_button_appears_for_unpaid_and_not_for_paid(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test11.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos11"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    paid_id = members_service.create_member(conn, {"first_name": "Riley", "mobile": "9000000555", "plan_id": plan_id})
    unpaid_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000556", "plan_id": plan_id})
    admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
    payments_service.mark_paid(conn, paid_id, plan_id, admin_id)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/payments.py")
    at.run()

    assert not at.exception
    with pytest.raises(KeyError):
        at.button(key=f"log_reminder_{paid_id}")
    assert at.button(key=f"log_reminder_{unpaid_id}").label == "Log Reminder"


def test_logging_reminder_updates_button_label(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test12.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos12"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000556", "plan_id": plan_id})
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/payments.py")
    at.run()

    at.button(key=f"log_reminder_{member_id}").click().run()

    assert not at.exception
    assert "Remind Again" in at.button(key=f"log_reminder_{member_id}").label
