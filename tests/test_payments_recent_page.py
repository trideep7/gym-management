import datetime

import pytest


def login_as_admin(at):
    at.text_input(key="login_username").input("admin").run()
    at.text_input(key="login_password").input("password").run()
    at.button(key="login_button").click().run()
    return at


def _fresh(tmp_path, monkeypatch, name):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / f"{name}.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / f"photos_{name}"))
    import db as db_module

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    return conn


def _admin_id(conn):
    return conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]


def _open(page="pages_/payments_recent.py"):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page(page)
    at.run()
    return at


def test_recent_page_lists_a_payment_made_today(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "recent1")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(
        conn, {"first_name": "Nima", "surname": "Syrti", "mobile": "9000000111", "plan_id": plan_id}
    )
    payments_service.mark_paid(conn, member_id, plan_id, _admin_id(conn), payment_method="online")
    conn.close()

    at = _open()

    assert not at.exception
    assert any("Nima Syrti" in el.value for el in at.markdown)
    assert any("Monthly" in el.value for el in at.markdown)
    assert any("Online" in el.value for el in at.markdown)
    assert any("Added" in el.value for el in at.markdown)


def test_recent_page_defaults_to_last_7_days(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "recent2")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "InRange", "mobile": "9000000111", "plan_id": plan_id})
    payments_service.mark_paid(conn, member_id, plan_id, _admin_id(conn), paid_on=datetime.date.today() - datetime.timedelta(days=3))

    old_member = members_service.create_member(conn, {"first_name": "TooOld", "mobile": "9000000222", "plan_id": plan_id})
    payments_service.mark_paid(conn, old_member, plan_id, _admin_id(conn))
    # simulate this second payment's *activity* having happened 30 days ago
    conn.execute(
        "UPDATE payments SET updated_at = ?, created_at = ? WHERE member_id = ?",
        (
            (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat(),
            (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat(),
            old_member,
        ),
    )
    conn.commit()
    conn.close()

    at = _open()

    assert not at.exception
    assert any("InRange" in el.value for el in at.markdown)
    assert not any("TooOld" in el.value for el in at.markdown)


def test_recent_page_can_switch_to_last_30_days(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "recent3")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "TwoWeeksAgo", "mobile": "9000000111", "plan_id": plan_id})
    payments_service.mark_paid(conn, member_id, plan_id, _admin_id(conn))
    conn.execute(
        "UPDATE payments SET updated_at = ?, created_at = ? WHERE member_id = ?",
        (
            (datetime.datetime.now() - datetime.timedelta(days=14)).isoformat(),
            (datetime.datetime.now() - datetime.timedelta(days=14)).isoformat(),
            member_id,
        ),
    )
    conn.commit()
    conn.close()

    at = _open()
    assert not any("TwoWeeksAgo" in el.value for el in at.markdown)

    at.selectbox(key="recent_payments_preset").select("Last 30 Days").run()

    assert not at.exception
    assert any("TwoWeeksAgo" in el.value for el in at.markdown)


def test_recent_page_shows_edited_for_a_touched_payment(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "recent4")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Edited", "mobile": "9000000111", "plan_id": plan_id})
    admin_id = _admin_id(conn)
    payment_id = payments_service.mark_paid(conn, member_id, plan_id, admin_id, paid_on="2026-01-01")
    payments_service.update_payment(conn, payment_id, payment_method="online", paid_on="2026-01-01", amount=1500.0)
    conn.close()

    at = _open()

    assert not at.exception
    assert any("Edited" in el.value for el in at.markdown)
    assert any("Edited " in el.value for el in at.markdown)  # the activity label, not just the member's name


def test_recent_page_search_filters_by_name(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "recent5")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    admin_id = _admin_id(conn)
    asha_id = members_service.create_member(conn, {"first_name": "Asha", "mobile": "9000000111", "plan_id": plan_id})
    payments_service.mark_paid(conn, asha_id, plan_id, admin_id)
    riya_id = members_service.create_member(conn, {"first_name": "Riya", "mobile": "9000000222", "plan_id": plan_id})
    payments_service.mark_paid(conn, riya_id, plan_id, admin_id)
    conn.close()

    at = _open()
    at.text_input(key="recent_payments_search").input("Asha").run()

    assert not at.exception
    assert any("Asha" in el.value for el in at.markdown)
    assert not any("Riya" in el.value for el in at.markdown)


def test_recent_page_empty_state_for_no_activity(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "recent6")
    conn.close()

    at = _open()

    assert not at.exception
    assert any("no payment activity" in el.value.lower() for el in at.info)


def test_recent_page_paginates(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "recent7")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    admin_id = _admin_id(conn)
    for i in range(25):
        member_id = members_service.create_member(
            conn, {"first_name": f"Member{i:02d}", "mobile": f"90000006{i:02d}", "plan_id": plan_id}
        )
        payments_service.mark_paid(conn, member_id, plan_id, admin_id)
    conn.close()

    at = _open()

    assert not at.exception
    assert len([el for el in at.markdown if el.value.startswith("Member")]) == 20

    at.button(key="recent_payments_page_next").click().run()

    assert not at.exception
    assert len([el for el in at.markdown if el.value.startswith("Member")]) == 5


def test_staff_cannot_access_recent_payments_page_is_not_relevant(tmp_path, monkeypatch):
    # unlike Reports/Settings, this page has no role restriction -- staff
    # need it just as much as admins to see recent payment activity
    conn = _fresh(tmp_path, monkeypatch, "recent8")
    from services import members as members_service
    from services import payments as payments_service
    from services import auth as auth_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    payments_service.mark_paid(conn, member_id, plan_id, _admin_id(conn))
    auth_service.create_user(conn, "frontdesk", "pw123456", "Front Desk", "staff")
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    at.text_input(key="login_username").input("frontdesk").run()
    at.text_input(key="login_password").input("pw123456").run()
    at.button(key="login_button").click().run()
    at.switch_page("pages_/payments_recent.py")
    at.run()

    assert not at.exception
    assert any("Sam" in el.value for el in at.markdown)


# --- editing and deleting from this page ----------------------------------

def _seed_one_payment(tmp_path, monkeypatch, name):
    conn = _fresh(tmp_path, monkeypatch, name)
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    payment_id = payments_service.mark_paid(conn, member_id, plan_id, _admin_id(conn), payment_method="offline")
    conn.close()
    return payment_id


def test_recent_page_edit_opens_a_form_prefilled_with_existing_values(tmp_path, monkeypatch):
    payment_id = _seed_one_payment(tmp_path, monkeypatch, "recentedit1")

    at = _open()
    at.button(key=f"recent_edit_payment_{payment_id}").click().run()

    assert not at.exception
    # .options are format_func'd display labels; .value/.select() operate
    # on the raw plan id -- with one plan on file, it being the sole
    # option is enough to prove the right plan is showing
    assert at.selectbox(key=f"recent_edit_plan_{payment_id}").options == ["Monthly"]
    assert at.number_input(key=f"recent_edit_amount_{payment_id}").value == 1500.0
    assert at.radio(key=f"recent_edit_payment_method_{payment_id}").value == "Offline"
    assert at.button(key=f"recent_save_payment_{payment_id}")
    assert at.button(key=f"recent_delete_payment_{payment_id}")
    assert at.button(key=f"recent_cancel_edit_payment_{payment_id}")


def test_recent_page_can_change_the_plan(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "recentplan1")
    from services import members as members_service
    from services import payments as payments_service

    monthly_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    registration_id = payments_service.create_plan(conn, "Registration (3-Month)", 4000.0, 90)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": monthly_id})
    payment_id = payments_service.mark_paid(conn, member_id, monthly_id, _admin_id(conn))
    conn.close()

    at = _open()
    at.button(key=f"recent_edit_payment_{payment_id}").click().run()
    at.selectbox(key=f"recent_edit_plan_{payment_id}").select(registration_id).run()
    at.number_input(key=f"recent_edit_amount_{payment_id}").set_value(4000.0).run()
    at.button(key=f"recent_save_payment_{payment_id}").click().run()

    assert not at.exception
    assert any("Registration (3-Month)" in el.value for el in at.markdown)


def test_recent_page_save_updates_the_payment(tmp_path, monkeypatch):
    payment_id = _seed_one_payment(tmp_path, monkeypatch, "recentedit2")

    at = _open()
    at.button(key=f"recent_edit_payment_{payment_id}").click().run()
    at.number_input(key=f"recent_edit_amount_{payment_id}").set_value(1200.0).run()
    at.radio(key=f"recent_edit_payment_method_{payment_id}").set_value("Online").run()
    at.button(key=f"recent_save_payment_{payment_id}").click().run()

    assert not at.exception
    assert "updated" in at.success[0].value.lower()
    assert any("₹1200.00" in el.value for el in at.markdown)
    assert any("Online" in el.value for el in at.markdown)


def test_recent_page_cancel_discards_without_saving(tmp_path, monkeypatch):
    payment_id = _seed_one_payment(tmp_path, monkeypatch, "recentedit3")

    at = _open()
    at.button(key=f"recent_edit_payment_{payment_id}").click().run()
    at.button(key=f"recent_cancel_edit_payment_{payment_id}").click().run()

    assert not at.exception
    with pytest.raises(KeyError):
        at.button(key=f"recent_save_payment_{payment_id}")
    assert any("₹1500.00" in el.value for el in at.markdown)


def test_recent_page_delete_asks_for_confirmation_first(tmp_path, monkeypatch):
    payment_id = _seed_one_payment(tmp_path, monkeypatch, "recentedit4")

    at = _open()
    at.button(key=f"recent_edit_payment_{payment_id}").click().run()
    at.button(key=f"recent_delete_payment_{payment_id}").click().run()

    assert not at.exception
    assert any("delete" in el.value.lower() for el in at.warning)
    assert at.button(key=f"recent_confirm_delete_payment_{payment_id}")
    assert at.button(key=f"recent_cancel_delete_payment_{payment_id}")
    assert any("Sam" in el.value for el in at.markdown)  # not deleted yet


def test_recent_page_delete_confirm_removes_it(tmp_path, monkeypatch):
    payment_id = _seed_one_payment(tmp_path, monkeypatch, "recentedit5")

    at = _open()
    at.button(key=f"recent_edit_payment_{payment_id}").click().run()
    at.button(key=f"recent_delete_payment_{payment_id}").click().run()
    at.button(key=f"recent_confirm_delete_payment_{payment_id}").click().run()

    assert not at.exception
    assert "deleted" in at.success[0].value.lower()
    assert any("no payment activity" in el.value.lower() for el in at.info)


def test_recent_page_delete_cancel_keeps_it(tmp_path, monkeypatch):
    payment_id = _seed_one_payment(tmp_path, monkeypatch, "recentedit6")

    at = _open()
    at.button(key=f"recent_edit_payment_{payment_id}").click().run()
    at.button(key=f"recent_delete_payment_{payment_id}").click().run()
    at.button(key=f"recent_cancel_delete_payment_{payment_id}").click().run()

    assert not at.exception
    assert at.button(key=f"recent_save_payment_{payment_id}")  # back to the edit form


# --- who touched it ---------------------------------------------------------

def test_recent_page_shows_who_recorded_a_new_payment(tmp_path, monkeypatch):
    _seed_one_payment(tmp_path, monkeypatch, "recentwho1")

    at = _open()

    assert not at.exception
    assert any("Added" in el.value and "Admin (Administrator)" in el.value for el in at.markdown)


def test_recent_page_shows_the_staff_member_who_edited_it(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "recentwho2")
    from services import auth as auth_service
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    payment_id = payments_service.mark_paid(conn, member_id, plan_id, _admin_id(conn))
    auth_service.create_user(conn, "frontdesk", "pw123456", "Front Desk", "staff")
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    at.text_input(key="login_username").input("frontdesk").run()
    at.text_input(key="login_password").input("pw123456").run()
    at.button(key="login_button").click().run()
    at.switch_page("pages_/payments_recent.py")
    at.run()

    at.button(key=f"recent_edit_payment_{payment_id}").click().run()
    at.radio(key=f"recent_edit_payment_method_{payment_id}").set_value("Online").run()
    at.button(key=f"recent_save_payment_{payment_id}").click().run()

    assert not at.exception
    assert any("Edited" in el.value and "Staff (Front Desk)" in el.value for el in at.markdown)


def test_recent_page_shows_system_when_unattributed(tmp_path, monkeypatch):
    # e.g. a payment touched by a script or maintenance task rather than
    # a logged-in staff/admin action
    conn = _fresh(tmp_path, monkeypatch, "recentwho3")
    from services import members as members_service
    from services import payments as payments_service

    import time

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    payment_id = payments_service.mark_paid(conn, member_id, plan_id, _admin_id(conn), paid_on="2026-01-15")
    time.sleep(0.01)
    payments_service.update_payment(conn, payment_id, payment_method="online", paid_on="2026-01-15", amount=1500.0)
    conn.close()

    at = _open()

    assert not at.exception
    assert any("Edited" in el.value and "System" in el.value for el in at.markdown)
