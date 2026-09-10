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


def test_search_results_show_view_button_not_inline_edit_fields(tmp_path, monkeypatch):
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
    with pytest.raises(KeyError):
        at.button(key=f"edit_button_{member_id}")
    with pytest.raises(KeyError):
        at.button(key=f"toggle_active_{member_id}")
    assert at.button(key=f"view_button_{member_id}")


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

    at.button(key=f"view_button_{member_id}").click().run()
    at.button(key=f"edit_from_view_{member_id}").click().run()

    assert not at.exception
    assert at.text_input(key=f"edit_{member_id}_first_name").value == "Riley"

    at.text_input(key=f"edit_{member_id}_occupation").input("Engineer").run()
    at.button(key=f"save_edit_{member_id}").click().run()

    assert not at.exception
    assert "updated" in at.success[0].value.lower()

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
    # exactly 20 View buttons on page 1, not all 25
    edit_buttons = [b for b in at.button if b.key and b.key.startswith("view_button_")]
    assert len(edit_buttons) == 20

    at.button(key="member_list_page_next").click().run()

    assert not at.exception
    edit_buttons_page2 = [b for b in at.button if b.key and b.key.startswith("view_button_")]
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

    at.button(key="member_list_page_next").click().run()
    assert any("Page 2 of 2" in el.value for el in at.markdown)

    at.text_input(key="member_search_query").input("Unique").run()

    assert not at.exception
    assert any("1 member" in el.value for el in at.markdown)
    with pytest.raises(KeyError):
        at.button(key="member_list_page_next")


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

    at.button(key=f"view_button_{member_id}").click().run()
    at.button(key=f"toggle_active_view_{member_id}").click().run()

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
    # way to reach it
    assert not any("Casey" in el.value for el in at.markdown)
    with pytest.raises(KeyError):
        at.button(key=f"view_button_{member_id}")

    at.checkbox(key="member_show_inactive").set_value(True).run()

    assert any("Casey" in el.value for el in at.markdown)
    at.button(key=f"view_button_{member_id}").click().run()

    assert any("Inactive" in el.value for el in at.markdown)
    reactivate_button = at.button(key=f"toggle_active_view_{member_id}")
    assert reactivate_button.label == "Reactivate Member"

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


def test_view_screen_shows_contact_info_and_payment_history(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test15.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos15"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(
        conn, {"first_name": "Riley", "surname": "Fox", "mobile": "9000000555", "email": "riley@example.com", "plan_id": plan_id}
    )
    admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
    payments_service.mark_paid(conn, member_id, plan_id, admin_id)
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()

    at.button(key=f"view_button_{member_id}").click().run()

    assert not at.exception
    assert any("Riley Fox" in el.value for el in at.subheader)
    assert any("9000000555" in el.value for el in at.markdown)
    assert any("Monthly" in el.value for el in at.markdown)
    # email is stored but deliberately not shown on this screen
    assert not any("riley@example.com" in el.value for el in at.markdown)
    assert not any("Email" in el.value for el in at.markdown)
    # a paid, active member shouldn't be offered a reminder button
    with pytest.raises(KeyError):
        at.button(key=f"log_reminder_{member_id}")
    assert at.button(key=f"edit_from_view_{member_id}")
    assert at.button(key=f"toggle_active_view_{member_id}")


def test_view_screen_shows_last_10_signins(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test18.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos18"))
    import datetime

    import db as db_module
    from services import attendance as attendance_service
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Riley", "mobile": "9000000555", "plan_id": plan_id})
    admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
    base = datetime.datetime(2026, 8, 1, 9, 0, 0)
    for i in range(12):
        attendance_service.sign_in(conn, member_id, admin_id, when=base + datetime.timedelta(days=i))
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()

    at.button(key=f"view_button_{member_id}").click().run()

    assert not at.exception
    markdown_values = [el.value for el in at.markdown]
    # Date and Time as separate columns with a header row
    assert "**Date**" in markdown_values
    assert "**Time**" in markdown_values
    # newest of the 12 sign-ins (Aug 12) shown, oldest two (Aug 1, Aug 2) not
    assert "12-Aug-2026" in markdown_values
    assert "09:00 AM" in markdown_values
    assert not any("01-Aug-2026" in v for v in markdown_values)
    assert not any("02-Aug-2026" in v for v in markdown_values)


# --- editing a payment from the member view screen -----------------------

def _open_view_with_one_payment(tmp_path, monkeypatch, name, payment_method=None, paid_on=None):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / f"{name}.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / f"photos_{name}"))
    import datetime

    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Riley", "mobile": "9000000555", "plan_id": plan_id})
    admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
    paid_on = paid_on or datetime.date(2026, 1, 15)
    payment_id = payments_service.mark_paid(
        conn, member_id, plan_id, admin_id, paid_on=paid_on, payment_method=payment_method
    )
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()
    at.button(key=f"view_button_{member_id}").click().run()

    return at, member_id, payment_id, paid_on


def test_view_screen_shows_payment_method_column(tmp_path, monkeypatch):
    at, member_id, payment_id, paid_on = _open_view_with_one_payment(
        tmp_path, monkeypatch, "editpay1", payment_method="online"
    )

    assert not at.exception
    markdown_values = [el.value for el in at.markdown]
    assert "**Method**" in markdown_values
    assert "Online" in markdown_values
    assert at.button(key=f"edit_payment_{payment_id}")


def test_view_screen_shows_a_dash_for_payments_with_no_recorded_method(tmp_path, monkeypatch):
    at, member_id, payment_id, paid_on = _open_view_with_one_payment(tmp_path, monkeypatch, "editpay2")

    assert not at.exception
    assert "—" in [el.value for el in at.markdown]


def test_edit_payment_opens_a_form_prefilled_with_existing_values(tmp_path, monkeypatch):
    at, member_id, payment_id, paid_on = _open_view_with_one_payment(
        tmp_path, monkeypatch, "editpay3", payment_method="offline"
    )

    at.button(key=f"edit_payment_{payment_id}").click().run()

    assert not at.exception
    # the Selectbox wrapper's .options are format_func'd display labels,
    # but .value/.select() operate on the raw option (the plan id) --
    # with only one plan on file, its label being the sole option is
    # enough to prove it's showing (and thus selecting) the right plan
    assert at.selectbox(key=f"edit_plan_{payment_id}").options == ["Monthly"]
    assert at.number_input(key=f"edit_amount_{payment_id}").value == 1500.0
    assert at.date_input(key=f"edit_paid_on_{payment_id}").value == paid_on
    assert at.radio(key=f"edit_payment_method_{payment_id}").value == "Offline"
    assert at.button(key=f"save_payment_{payment_id}")
    assert at.button(key=f"delete_payment_{payment_id}")
    assert at.button(key=f"cancel_edit_payment_{payment_id}")


def test_edit_payment_can_change_the_plan(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "editplan1.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos_editplan1"))
    import datetime

    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    monthly_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    registration_id = payments_service.create_plan(conn, "Registration (3-Month)", 4000.0, 90)
    member_id = members_service.create_member(conn, {"first_name": "Riley", "mobile": "9000000555", "plan_id": monthly_id})
    admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
    payment_id = payments_service.mark_paid(conn, member_id, monthly_id, admin_id, paid_on=datetime.date(2026, 1, 15))
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()
    at.button(key=f"view_button_{member_id}").click().run()

    at.button(key=f"edit_payment_{payment_id}").click().run()
    at.selectbox(key=f"edit_plan_{payment_id}").select(registration_id).run()
    at.number_input(key=f"edit_amount_{payment_id}").set_value(4000.0).run()
    at.button(key=f"save_payment_{payment_id}").click().run()

    assert not at.exception
    check = db_module.get_connection()
    updated = payments_service.payment_history(check, member_id)[0]
    assert updated["plan_name"] == "Registration (3-Month)"
    assert updated["period_start"] == "2026-01-15"
    assert updated["valid_until"] == "2026-04-15"  # 90 days from the unchanged anchor
    check.close()


def test_edit_payment_opens_without_crashing_when_paid_on_is_in_the_future(tmp_path, monkeypatch):
    # a member can legitimately pay ahead for a cycle that starts next
    # month -- paid_on beyond today is real, valid data, not corruption
    import datetime

    future_paid_on = datetime.date.today() + datetime.timedelta(days=45)
    at, member_id, payment_id, paid_on = _open_view_with_one_payment(
        tmp_path, monkeypatch, "editpay9", paid_on=future_paid_on
    )

    at.button(key=f"edit_payment_{payment_id}").click().run()

    assert not at.exception
    assert at.date_input(key=f"edit_paid_on_{payment_id}").value == future_paid_on


def test_edit_payment_save_updates_method_and_date(tmp_path, monkeypatch):
    import datetime

    at, member_id, payment_id, paid_on = _open_view_with_one_payment(
        tmp_path, monkeypatch, "editpay4", payment_method="offline"
    )
    new_date = datetime.date(2026, 1, 20)

    at.button(key=f"edit_payment_{payment_id}").click().run()
    at.date_input(key=f"edit_paid_on_{payment_id}").set_value(new_date).run()
    at.radio(key=f"edit_payment_method_{payment_id}").set_value("Online").run()
    at.button(key=f"save_payment_{payment_id}").click().run()

    assert not at.exception
    assert "updated" in at.success[0].value.lower()

    import db as db_module
    from services import payments as payments_service

    check = db_module.get_connection()
    updated = payments_service.payment_history(check, member_id)[0]
    assert updated["paid_on"] == new_date.isoformat()
    assert updated["payment_method"] == "online"
    check.close()


def test_edit_payment_save_updates_the_amount(tmp_path, monkeypatch):
    at, member_id, payment_id, paid_on = _open_view_with_one_payment(tmp_path, monkeypatch, "editpay10")

    at.button(key=f"edit_payment_{payment_id}").click().run()
    at.number_input(key=f"edit_amount_{payment_id}").set_value(1200.0).run()
    at.button(key=f"save_payment_{payment_id}").click().run()

    assert not at.exception

    import db as db_module
    from services import payments as payments_service

    check = db_module.get_connection()
    assert payments_service.payment_history(check, member_id)[0]["amount"] == 1200.0
    check.close()


def test_edit_payment_cancel_discards_without_saving(tmp_path, monkeypatch):
    at, member_id, payment_id, paid_on = _open_view_with_one_payment(
        tmp_path, monkeypatch, "editpay5", payment_method="offline"
    )

    at.button(key=f"edit_payment_{payment_id}").click().run()
    at.button(key=f"cancel_edit_payment_{payment_id}").click().run()

    assert not at.exception
    with pytest.raises(KeyError):
        at.button(key=f"save_payment_{payment_id}")
    assert at.button(key=f"edit_payment_{payment_id}")

    import db as db_module
    from services import payments as payments_service

    check = db_module.get_connection()
    unchanged = payments_service.payment_history(check, member_id)[0]
    assert unchanged["payment_method"] == "offline"
    check.close()


def test_edit_payment_delete_asks_for_confirmation_first(tmp_path, monkeypatch):
    at, member_id, payment_id, paid_on = _open_view_with_one_payment(tmp_path, monkeypatch, "editpay6")

    at.button(key=f"edit_payment_{payment_id}").click().run()
    at.button(key=f"delete_payment_{payment_id}").click().run()

    assert not at.exception
    assert any("delete" in el.value.lower() for el in at.warning)
    assert at.button(key=f"confirm_delete_payment_{payment_id}")
    assert at.button(key=f"cancel_delete_payment_{payment_id}")

    import db as db_module
    from services import payments as payments_service

    check = db_module.get_connection()
    assert len(payments_service.payment_history(check, member_id)) == 1
    check.close()


def test_edit_payment_delete_confirm_removes_it(tmp_path, monkeypatch):
    at, member_id, payment_id, paid_on = _open_view_with_one_payment(tmp_path, monkeypatch, "editpay7")

    at.button(key=f"edit_payment_{payment_id}").click().run()
    at.button(key=f"delete_payment_{payment_id}").click().run()
    at.button(key=f"confirm_delete_payment_{payment_id}").click().run()

    assert not at.exception
    assert "deleted" in at.success[0].value.lower()

    import db as db_module
    from services import payments as payments_service

    check = db_module.get_connection()
    assert payments_service.payment_history(check, member_id) == []
    check.close()


def test_edit_payment_delete_cancel_keeps_it(tmp_path, monkeypatch):
    at, member_id, payment_id, paid_on = _open_view_with_one_payment(tmp_path, monkeypatch, "editpay8")

    at.button(key=f"edit_payment_{payment_id}").click().run()
    at.button(key=f"delete_payment_{payment_id}").click().run()
    at.button(key=f"cancel_delete_payment_{payment_id}").click().run()

    assert not at.exception
    # back to the edit form, not the confirmation
    assert at.button(key=f"save_payment_{payment_id}")
    assert at.button(key=f"delete_payment_{payment_id}")

    import db as db_module
    from services import payments as payments_service

    check = db_module.get_connection()
    assert len(payments_service.payment_history(check, member_id)) == 1
    check.close()


def test_edit_from_view_returns_to_view_not_list(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test16.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos16"))
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

    at.button(key=f"view_button_{member_id}").click().run()
    at.button(key=f"edit_from_view_{member_id}").click().run()

    assert not at.exception
    assert at.text_input(key=f"edit_{member_id}_first_name").value == "Riley"

    at.text_input(key=f"edit_{member_id}_occupation").input("Engineer").run()
    at.button(key=f"save_edit_{member_id}").click().run()

    assert not at.exception
    assert "updated" in at.success[0].value.lower()
    # back on View (not the list): the View screen's own buttons are there,
    # the edit form's fields are gone, and the list's search box is gone
    assert at.button(key=f"edit_from_view_{member_id}")
    with pytest.raises(KeyError):
        at.text_input(key=f"edit_{member_id}_first_name")
    with pytest.raises(KeyError):
        at.text_input(key="member_search_query")


def test_reminder_log_button_appears_for_unpaid_member_and_logs(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test17.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos17"))
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

    at.button(key=f"view_button_{member_id}").click().run()

    assert not at.exception
    assert any("No reminders logged yet" in el.value for el in at.markdown)

    at.button(key=f"log_reminder_{member_id}").click().run()

    assert not at.exception
    assert any("Sent by Administrator" in el.value for el in at.markdown)
    # the member is still unpaid, so the button to log another reminder
    # must still be offered (not hidden after the first one)
    assert at.button(key=f"log_reminder_{member_id}")


def test_member_form_has_personal_trainer_selectbox_defaulting_to_none(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test20.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos20"))
    import db as db_module
    from services import payments as payments_service
    from services import trainers as trainers_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    payments_service.create_plan(conn, "Monthly", 1000.0, 30)
    trainers_service.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()

    at.button(key="show_add_member_button").click().run()

    trainer_select = at.selectbox(key="add_trainer_id")
    assert trainer_select.value is None
    # .options holds the format_func-rendered display strings, not the raw
    # option values (which include the real None) — see .value above for that.
    assert "None" in trainer_select.options


def test_assigning_and_clearing_trainer_persists(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test21.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos21"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service
    from services import trainers as trainers_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1000.0, 30)
    trainer_id = trainers_service.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()

    at.button(key=f"view_button_{member_id}").click().run()
    at.button(key=f"edit_from_view_{member_id}").click().run()
    at.selectbox(key=f"edit_{member_id}_trainer_id").select(trainer_id).run()
    at.button(key=f"save_edit_{member_id}").click().run()

    assert not at.exception
    conn2 = db_module.get_connection(str(tmp_path / "test21.db"))
    assert members_service.get_member(conn2, member_id)["trainer_id"] == trainer_id
    conn2.close()


def test_edit_form_shows_currently_assigned_trainer(tmp_path, monkeypatch):
    # The reverse direction (selecting the "None" entry in the browser and
    # having it persist) is covered by tests/test_members.py's
    # test_trainer_id_round_trips_through_create_and_update at the service
    # layer, and verified in a real browser during manual QA — AppTest's
    # Selectbox can't simulate explicitly choosing an option whose
    # underlying value is None: its _widget_state only sets string_value
    # when .index is not None, and .index itself returns None whenever
    # .value is None, so there's no way to distinguish "the None option is
    # selected" from "nothing was selected" through this test harness.
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test22.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos22"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service
    from services import trainers as trainers_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1000.0, 30)
    trainer_id = trainers_service.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    member_id = members_service.create_member(
        conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id, "trainer_id": trainer_id}
    )
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()

    at.button(key=f"view_button_{member_id}").click().run()
    at.button(key=f"edit_from_view_{member_id}").click().run()

    assert not at.exception
    assert at.selectbox(key=f"edit_{member_id}_trainer_id").value == trainer_id


def test_add_member_form_shows_locker_availability(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test_lockercap.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos_lockercap"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service
    from services import settings as settings_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    settings_service.set_locker_count(conn, 10)
    for i in range(4):
        members_service.create_member(
            conn,
            {"first_name": f"Holder{i}", "mobile": f"90000006{i:02d}",
             "plan_id": plan_id, "has_locker": True},
        )
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()
    at.button(key="show_add_member_button").click().run()

    assert not at.exception
    assert any("4 of 10 lockers in use" in el.value for el in at.caption)


def test_add_member_form_says_nothing_about_lockers_when_no_total_is_set(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test_nolockercap.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos_nolockercap"))
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

    assert not at.exception
    assert not any("lockers in use" in el.value for el in at.caption)


def test_saving_a_member_over_the_locker_limit_shows_a_friendly_error(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test_lockerfull.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos_lockerfull"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service
    from services import settings as settings_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    settings_service.set_locker_count(conn, 1)
    members_service.create_member(
        conn, {"first_name": "Holder", "mobile": "9000000700", "plan_id": plan_id, "has_locker": True}
    )
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()
    at.button(key="show_add_member_button").click().run()

    at.text_input(key="add_first_name").input("Asha").run()
    at.checkbox(key="add_has_locker").check().run()
    at.button(key="save_new_member").click().run()

    assert not at.exception
    assert any("lockers are in use" in el.value for el in at.error)


def test_member_time_slot_offers_the_same_options_as_the_trainer_form(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test_slots_m1.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos_slots_m1"))
    import db as db_module
    from services import payments as payments_service
    from services import time_slots as time_slots_service
    from utils import time_slots

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

    assert not at.exception
    check = db_module.get_connection()
    expected_labels = [s["label"] for s in time_slots_service.list_time_slots(check)]
    check.close()
    assert at.selectbox(key="add_time_slot").options == [time_slots.NOT_SET] + expected_labels


def test_a_new_member_with_no_slot_chosen_is_stored_without_one(tmp_path, monkeypatch):
    # the form used to default to the first slot, silently assigning
    # everyone a 6-8 AM preference they never picked
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test_slots_m2.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos_slots_m2"))
    import db as db_module
    from services import members as members_service
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
    at.text_input(key="add_first_name").input("Asha").run()
    at.button(key="save_new_member").click().run()

    assert not at.exception
    check = db_module.get_connection()
    assert members_service.search_members(check, "Asha")[0]["preferred_time_slot"] is None
    check.close()


def test_editing_a_member_with_no_slot_does_not_invent_one(tmp_path, monkeypatch):
    # every imported member has a NULL slot; opening and saving their
    # record must not stamp them with the first option
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test_slots_m3.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos_slots_m3"))
    import db as db_module
    from services import members as members_service
    from services import payments as payments_service

    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(
        conn, {"first_name": "Ravi", "mobile": "9000000801", "plan_id": plan_id}
    )
    conn.execute("UPDATE members SET preferred_time_slot = NULL WHERE id = ?", (member_id,))
    conn.commit()
    conn.close()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/members.py")
    at.run()
    at.button(key=f"view_button_{member_id}").click().run()
    at.button(key=f"edit_from_view_{member_id}").click().run()

    assert at.selectbox(key=f"edit_{member_id}_time_slot").value == "Not set"

    at.button(key=f"save_edit_{member_id}").click().run()

    assert not at.exception
    check = db_module.get_connection()
    assert members_service.get_member(check, member_id)["preferred_time_slot"] is None
    check.close()
