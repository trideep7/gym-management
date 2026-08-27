import datetime


def login_as_admin(at):
    at.text_input(key="login_username").input("admin").run()
    at.text_input(key="login_password").input("password").run()
    at.button(key="login_button").click().run()
    return at


def open_reports_page(tmp_path, monkeypatch, db_name="test.db", photos_name="photos"):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / db_name))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / photos_name))
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/reports.py")
    at.run()
    return at


def test_top_stats_render_without_generating_a_report(tmp_path, monkeypatch):
    import db as db_module
    from services import members, payments

    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos"))
    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1500.0, 30)
    inactive_id = members.create_member(conn, {"first_name": "Gone", "mobile": "9000000111", "plan_id": plan_id})
    members.set_member_active(conn, inactive_id, False)
    conn.close()

    at = open_reports_page(tmp_path, monkeypatch)

    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Due (Inactive)"] == "₹1500.00"
    assert metrics["Due (Active)"] == "₹0.00"
    assert metrics["Payments Overdue"] == "0"
    assert "Revenue This Month" in metrics
    assert "Revenue This Year" in metrics
    assert "Active Members" in metrics
    subheaders = {el.value for el in at.subheader}
    assert "Last 12 Months Revenue" in subheaders
    # nothing generated yet — the date-range-driven charts must not show
    assert "Sign-Ins" not in subheaders
    assert "Revenue Collected" not in subheaders


def test_default_preset_hides_manual_date_inputs(tmp_path, monkeypatch):
    at = open_reports_page(tmp_path, monkeypatch)
    assert len(at.date_input) == 0


def test_custom_preset_reveals_manual_date_inputs(tmp_path, monkeypatch):
    at = open_reports_page(tmp_path, monkeypatch)
    at.selectbox(key="report_preset").select("Custom").run()
    assert {d.key for d in at.date_input} == {"report_start", "report_end"}


def test_from_after_to_shows_warning_not_empty_report(tmp_path, monkeypatch):
    at = open_reports_page(tmp_path, monkeypatch, "test2.db", "photos2")
    at.selectbox(key="report_preset").select("Custom").run()

    at.date_input(key="report_start").set_value(datetime.date(2026, 8, 24)).run()
    at.date_input(key="report_end").set_value(datetime.date(2026, 8, 18)).run()
    at.button[0].click().run()

    assert not at.exception
    assert any("from date" in el.value.lower() and "to date" in el.value.lower() for el in at.warning)
    # must not have gone ahead and rendered a (misleadingly empty) report
    assert not any(el.value == "Sign-Ins" for el in at.subheader)


def test_generating_a_report_shows_signin_and_revenue_charts(tmp_path, monkeypatch):
    at = open_reports_page(tmp_path, monkeypatch, "test3.db", "photos3")
    at.selectbox(key="report_preset").select("Today").run()
    at.button[0].click().run()

    assert not at.exception
    subheaders = {el.value for el in at.subheader}
    assert "Sign-Ins" in subheaders
    assert "Revenue Collected" in subheaders


def test_generating_a_report_shows_personal_training_section(tmp_path, monkeypatch):
    import db as db_module
    from services import members, payments, trainers as trainers_service

    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test5.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos5"))
    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    trainer_id = trainers_service.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id, "trainer_id": trainer_id})
    admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
    trainers_service.record_trainer_payment(conn, member_id, trainer_id, 3000, 2000, admin_id)
    conn.close()

    at = open_reports_page(tmp_path, monkeypatch, "test5.db", "photos5")
    at.selectbox(key="report_preset").select("This Year").run()
    at.button[0].click().run()

    assert not at.exception
    subheaders = {el.value for el in at.subheader}
    assert "Personal Training" in subheaders
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["PT Fees Collected"] == "₹3000.00"
    assert metrics["Owed to Trainers"] == "₹2000.00"
    assert metrics["Gym Share"] == "₹1000.00"
    assert any(el.value == "Alex" for el in at.markdown)


def test_personal_training_section_flags_unassigned_payouts(tmp_path, monkeypatch):
    # mirrors the real post-import state: members paying for PT, no trainer
    # roster yet. The money must still show up, clearly marked.
    import db as db_module
    from services import members, payments, trainers as trainers_service

    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test6.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos6"))
    conn = db_module.get_connection()
    db_module.init_db(conn)
    db_module.seed_admin(conn)
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    member_id = members.create_member(
        conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id, "has_pt": True}
    )
    admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
    trainers_service.mark_paid_with_pt(conn, member_id, plan_id, admin_id)
    conn.close()

    at = open_reports_page(tmp_path, monkeypatch, "test6.db", "photos6")
    at.button[0].click().run()

    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    # the fee was collected, so it must not report as zero
    assert metrics["PT Fees Collected"] == "₹3000.00"
    assert metrics["Owed to Trainers"] == "₹2000.00"
    assert metrics["Gym Share"] == "₹1000.00"
    assert any("Not assigned to a trainer" in el.value for el in at.markdown)
    assert any("without a trainer assigned" in el.value for el in at.caption)
