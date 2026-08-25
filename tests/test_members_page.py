import pytest


def login_as_admin(at):
    at.text_input(key="login_username").input("admin").run()
    at.text_input(key="login_password").input("password").run()
    at.button(key="login_button").click().run()
    return at


def test_add_form_hidden_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test0.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos0"))
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()

    assert not at.exception
    with pytest.raises(KeyError):
        at.text_input(key="add_first_name")
    assert at.button(key="show_add_member_button")
    assert at.text_input(key="member_search_query")


def test_add_member_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos"))
    import db as db_module
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()

    at.button(key="show_add_member_button").click().run()
    at.text_input(key="add_first_name").input("Jamie").run()
    at.text_input(key="add_mobile").input("9876543210").run()
    at.button(key="save_new_member").click().run()

    assert not at.exception
    assert "saved" in at.success[0].value.lower()

    import db as db_module

    conn = db_module.get_connection(str(tmp_path / "test.db"))
    row = conn.execute("SELECT plan_id FROM members WHERE first_name = 'Jamie'").fetchone()
    assert row["plan_id"] is not None
    conn.close()

    # reopening the Add form must not show what was just typed for Jamie
    at.button(key="show_add_member_button").click().run()
    assert at.text_input(key="add_first_name").value == ""
    assert at.text_input(key="add_mobile").value == ""


def test_add_form_warns_when_no_plans_exist(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test6.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos6"))
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()

    at.button(key="show_add_member_button").click().run()

    assert not at.exception
    assert any("add a membership plan first" in el.value.lower() for el in at.warning)
    with pytest.raises(KeyError):
        at.text_input(key="add_first_name")


def test_search_finds_added_member(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test2.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos2"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    members_service.create_member(conn, {"first_name": "Riley", "mobile": "9000000555", "plan_id": plan_id})
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()

    at.text_input(key="member_search_query").input("Riley").run()
    assert not at.exception
    assert any("1 member" in el.value for el in at.markdown)


def test_search_results_show_no_inline_edit_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test9.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos9"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Riley", "mobile": "9000000555", "plan_id": plan_id})
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()

    at.text_input(key="member_search_query").input("Riley").run()

    assert not at.exception
    with pytest.raises(KeyError):
        at.text_input(key=f"edit_{member_id}_first_name")
    assert at.button(key=f"edit_button_{member_id}")
    assert at.button(key=f"toggle_active_{member_id}")


def test_edit_member_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test10.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos10"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Riley", "mobile": "9000000555", "plan_id": plan_id})
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()

    at.text_input(key="member_search_query").input("Riley").run()
    at.button(key=f"edit_button_{member_id}").click().run()

    assert not at.exception
    assert at.text_input(key=f"edit_{member_id}_first_name").value == "Riley"

    at.text_input(key=f"edit_{member_id}_occupation").input("Engineer").run()
    at.button(key=f"save_edit_{member_id}").click().run()

    assert not at.exception
    assert "updated" in at.success[0].value.lower()
    # must land back on the list view, not stay on the edit view
    with pytest.raises(KeyError):
        at.text_input(key=f"edit_{member_id}_first_name")

    conn = db_module.get_connection(str(tmp_path / "test10.db"))
    row = conn.execute("SELECT occupation FROM members WHERE id = ?", (member_id,)).fetchone()
    assert row["occupation"] == "Engineer"
    conn.close()


def test_list_shows_header_row_and_separate_name_phone_columns(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test14.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos14"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    members_service.create_member(conn, {"first_name": "Riley", "surname": "Fox", "mobile": "9000005551", "plan_id": plan_id})
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()

    assert not at.exception
    markdown_values = [el.value for el in at.markdown]
    assert "**Name**" in markdown_values
    assert "**Phone**" in markdown_values
    assert "**Payment**" in markdown_values
    # name and phone must render as separate elements, not "Name — mobile" combined
    assert any(el.value == "Riley Fox" for el in at.markdown)
    assert any(el.value == "9000005551" for el in at.markdown)
    assert not any("Riley Fox — 9000005551" in el.value for el in at.markdown)


def test_list_shows_payment_status_badge(tmp_path, monkeypatch):
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
    at.switch_page("pages_/members.py")
    at.run()

    assert not at.exception
    assert any("Paid" in el.value for el in at.markdown)
    assert any("No payment yet" in el.value for el in at.markdown)


def test_list_paginates_at_20_members_per_page(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test12.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos12"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_ids = []
    for i in range(25):
        member_ids.append(
            members_service.create_member(
                conn, {"first_name": f"Member{i:02d}", "mobile": f"9{i:09d}", "plan_id": plan_id}
            )
        )
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()

    assert not at.exception
    assert any("25 member" in el.value for el in at.markdown)
    # exactly 20 Edit buttons on page 1, not all 25
    edit_buttons = [b for b in at.button if b.key and b.key.startswith("edit_button_")]
    assert len(edit_buttons) == 20

    at.button(key="member_page_next").click().run()

    assert not at.exception
    edit_buttons_page2 = [b for b in at.button if b.key and b.key.startswith("edit_button_")]
    assert len(edit_buttons_page2) == 5
    assert any("Page 2 of 2" in el.value for el in at.markdown)


def test_list_resets_to_page_1_when_search_changes(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test13.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos13"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    for i in range(25):
        members_service.create_member(
            conn, {"first_name": f"Member{i:02d}", "mobile": f"9{i:09d}", "plan_id": plan_id}
        )
    members_service.create_member(conn, {"first_name": "Unique", "mobile": "1112223333", "plan_id": plan_id})
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()

    at.button(key="member_page_next").click().run()
    assert any("Page 2 of 2" in el.value for el in at.markdown)

    at.text_input(key="member_search_query").input("Unique").run()

    assert not at.exception
    assert any("1 member" in el.value for el in at.markdown)
    with pytest.raises(KeyError):
        at.button(key="member_page_next")


def test_toggle_active_failure_shows_friendly_message_not_traceback(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test10.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos10"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000333", "plan_id": plan_id})
    conn.close()

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(members_service, "set_member_active", boom)

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()

    at.button(key=f"toggle_active_{member_id}").click().run()

    assert not at.exception
    assert any("something went wrong" in el.value.lower() for el in at.error)


def test_deactivated_member_disappears_then_reappears_with_show_inactive(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test11.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos11"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Casey", "mobile": "9000000444", "plan_id": plan_id})
    members_service.set_member_active(conn, member_id, False)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()

    # deactivated, and the filter is off by default -> not in the list, no
    # way to reach the Reactivate button
    assert not any("Casey" in el.value for el in at.markdown)
    with pytest.raises(KeyError):
        at.button(key=f"toggle_active_{member_id}")

    at.checkbox(key="member_show_inactive").set_value(True).run()

    assert any("Casey" in el.value for el in at.markdown)
    reactivate_button = at.button(key=f"toggle_active_{member_id}")
    assert reactivate_button.label == "Reactivate"

    reactivate_button.click().run()
    assert not at.exception


def test_duplicate_mobile_shows_warning_but_still_allows_saving(tmp_path, monkeypatch):
    # Existing, already-correct behavior (warn, don't block — family members
    # sometimes share a number) — this locks it in with a test so a future
    # change to this page can't silently regress it.
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test12.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos12"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    members_service.create_member(conn, {"first_name": "Riley", "mobile": "9000000999", "plan_id": plan_id})
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()

    at.button(key="show_add_member_button").click().run()
    at.text_input(key="add_first_name").input("Jordan").run()
    at.text_input(key="add_mobile").input("9000000999").run()

    assert any("already use this mobile number" in el.value.lower() for el in at.warning)

    at.button(key="save_new_member").click().run()

    assert not at.exception
    assert "saved" in at.success[0].value.lower()
