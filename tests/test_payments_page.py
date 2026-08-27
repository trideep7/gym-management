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


def _open(page):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page(page)
    at.run()
    return at


OVERDUE = "pages_/payments_overdue.py"
UPCOMING = "pages_/payments_upcoming.py"
NEVER_PAID = "pages_/payments_never_paid.py"


# --- Never Paid ---------------------------------------------------------

def test_never_paid_page_lists_members_with_no_payment_on_record(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "np1")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    never_id = members_service.create_member(conn, {"first_name": "Neha", "mobile": "9000000111", "plan_id": plan_id})
    paid_id = members_service.create_member(conn, {"first_name": "Riley", "mobile": "9000000112", "plan_id": plan_id})
    payments_service.mark_paid(conn, paid_id, plan_id, _admin_id(conn))
    conn.close()

    at = _open(NEVER_PAID)

    assert not at.exception
    assert any("Neha" in el.value for el in at.markdown)
    assert not any("Riley" in el.value for el in at.markdown)
    assert at.button(key=f"mark_paid_{never_id}")


def test_never_paid_mark_paid_records_the_payment(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "np2")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    conn.close()

    at = _open(NEVER_PAID)
    at.button(key=f"mark_paid_{member_id}").click().run()

    assert not at.exception
    assert "paid" in at.success[0].value.lower()
    # the row must leave this page once they've paid
    assert not any("Sam" in el.value for el in at.markdown)


def test_never_paid_shows_members_own_plan_as_text_not_a_selectbox(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "np3")
    from services import members as members_service
    from services import payments as payments_service

    payments_service.create_plan(conn, "6 Months", 5000.0, 180)
    monthly_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": monthly_id})
    conn.close()

    at = _open(NEVER_PAID)

    assert not at.exception
    with pytest.raises(KeyError):
        at.selectbox(key=f"plan_select_{member_id}")
    assert any(el.value == "Monthly (₹1500.00)" for el in at.markdown)
    assert any("**Plan**" == el.value for el in at.markdown)
    assert any("**Mark Paid**" == el.value for el in at.markdown)


def test_mark_paid_disabled_when_member_has_no_plan(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "np4")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    # a legacy member from before plan_id existed
    conn.execute("UPDATE members SET plan_id = NULL WHERE id = ?", (member_id,))
    conn.commit()
    conn.close()

    at = _open(NEVER_PAID)

    assert not at.exception
    assert any(el.value == "No plan assigned" for el in at.markdown)
    assert at.button(key=f"mark_paid_{member_id}").disabled is True


def test_mark_paid_failure_shows_friendly_message_not_traceback(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "np5")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000555", "plan_id": plan_id})
    conn.close()

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(payments_service, "mark_paid", boom)

    at = _open(NEVER_PAID)
    at.button(key=f"mark_paid_{member_id}").click().run()

    assert not at.exception
    assert any("something went wrong" in el.value.lower() for el in at.error)


def test_never_paid_offers_a_reminder_button(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "np6")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000556", "plan_id": plan_id})
    conn.close()

    at = _open(NEVER_PAID)

    assert at.button(key=f"log_reminder_{member_id}").label == "Log Reminder"

    at.button(key=f"log_reminder_{member_id}").click().run()

    assert not at.exception
    assert "Remind Again" in at.button(key=f"log_reminder_{member_id}").label


def test_never_paid_page_paginates(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "np7")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    for i in range(25):
        members_service.create_member(
            conn, {"first_name": f"Never{i:02d}", "mobile": f"90000003{i:02d}", "plan_id": plan_id}
        )
    conn.close()

    at = _open(NEVER_PAID)

    assert not at.exception
    assert len([b for b in at.button if b.key and b.key.startswith("mark_paid_")]) == 20

    at.button(key="never_paid_page_next").click().run()

    assert not at.exception
    assert len([b for b in at.button if b.key and b.key.startswith("mark_paid_")]) == 5


# --- Overdue ------------------------------------------------------------

def test_overdue_page_lists_only_members_past_their_due_date(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "od1")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    admin_id = _admin_id(conn)
    today = datetime.date.today()

    lapsed_id = members_service.create_member(conn, {"first_name": "Lapsed", "mobile": "9000000111", "plan_id": plan_id})
    payments_service.mark_paid(conn, lapsed_id, plan_id, admin_id, paid_on=today - datetime.timedelta(days=45))

    current_id = members_service.create_member(conn, {"first_name": "Current", "mobile": "9000000112", "plan_id": plan_id})
    payments_service.mark_paid(conn, current_id, plan_id, admin_id, paid_on=today - datetime.timedelta(days=2))

    never_id = members_service.create_member(conn, {"first_name": "Never", "mobile": "9000000113", "plan_id": plan_id})
    conn.close()

    at = _open(OVERDUE)

    assert not at.exception
    assert any("Lapsed" in el.value for el in at.markdown)
    assert not any("Current" in el.value for el in at.markdown)
    # never-paid members have their own page
    assert not any("Never" in el.value for el in at.markdown)
    assert at.button(key=f"mark_paid_{lapsed_id}")
    with pytest.raises(KeyError):
        at.button(key=f"mark_paid_{never_id}")


def test_overdue_page_shows_the_last_payment_date(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "od2")
    from services import members as members_service
    from services import payments as payments_service
    from utils.dates import format_date

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Lapsed", "mobile": "9000000111", "plan_id": plan_id})
    paid_on = datetime.date.today() - datetime.timedelta(days=45)
    payments_service.mark_paid(conn, member_id, plan_id, _admin_id(conn), paid_on=paid_on)
    conn.close()

    at = _open(OVERDUE)

    assert not at.exception
    assert any(format_date(paid_on.isoformat()) in el.value for el in at.markdown)


def test_overdue_mark_paid_records_the_payment(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "od3")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Lapsed", "mobile": "9000000111", "plan_id": plan_id})
    payments_service.mark_paid(
        conn, member_id, plan_id, _admin_id(conn),
        paid_on=datetime.date.today() - datetime.timedelta(days=45),
    )
    conn.close()

    at = _open(OVERDUE)
    at.button(key=f"mark_paid_{member_id}").click().run()

    assert not at.exception
    assert "paid" in at.success[0].value.lower()
    assert not any("Lapsed" in el.value for el in at.markdown)


def test_overdue_page_paginates(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "od4")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    admin_id = _admin_id(conn)
    long_ago = datetime.date.today() - datetime.timedelta(days=60)
    for i in range(25):
        member_id = members_service.create_member(
            conn, {"first_name": f"Late{i:02d}", "mobile": f"90000004{i:02d}", "plan_id": plan_id}
        )
        payments_service.mark_paid(conn, member_id, plan_id, admin_id, paid_on=long_ago)
    conn.close()

    at = _open(OVERDUE)

    assert not at.exception
    assert len([b for b in at.button if b.key and b.key.startswith("mark_paid_")]) == 20

    at.button(key="overdue_page_next").click().run()

    assert not at.exception
    assert len([b for b in at.button if b.key and b.key.startswith("mark_paid_")]) == 5


# --- Upcoming -----------------------------------------------------------

def test_upcoming_page_lists_soonest_first_and_excludes_distant_expiries(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "up1")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    admin_id = _admin_id(conn)
    today = datetime.date.today()

    soon_id = members_service.create_member(conn, {"first_name": "Soon", "mobile": "9000000010", "plan_id": plan_id})
    payments_service.mark_paid(conn, soon_id, plan_id, admin_id, paid_on=today - datetime.timedelta(days=27))

    today_id = members_service.create_member(conn, {"first_name": "Today", "mobile": "9000000011", "plan_id": plan_id})
    payments_service.mark_paid(conn, today_id, plan_id, admin_id, paid_on=today - datetime.timedelta(days=30))

    members_service.create_member(conn, {"first_name": "NotSoon", "mobile": "9000000012", "plan_id": plan_id})
    payments_service.mark_paid(
        conn, conn.execute("SELECT id FROM members WHERE first_name='NotSoon'").fetchone()["id"],
        plan_id, admin_id, paid_on=today - datetime.timedelta(days=5),
    )
    conn.close()

    at = _open(UPCOMING)

    assert not at.exception
    values = [el.value for el in at.markdown]
    assert values.index("Today") < values.index("Soon")
    # a member with three weeks left isn't expiring soon
    assert not any("NotSoon" in v for v in values)


def test_upcoming_page_logs_a_reminder(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "up2")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Soon", "mobile": "9000000010", "plan_id": plan_id})
    payments_service.mark_paid(
        conn, member_id, plan_id, _admin_id(conn),
        paid_on=datetime.date.today() - datetime.timedelta(days=28),
    )
    conn.close()

    at = _open(UPCOMING)
    at.button(key=f"log_reminder_{member_id}").click().run()

    assert not at.exception
    assert "Remind Again" in at.button(key=f"log_reminder_{member_id}").label


def test_upcoming_page_can_take_an_early_payment_without_moving_the_cycle(tmp_path, monkeypatch):
    # paying a few days early is exactly what this page is for
    conn = _fresh(tmp_path, monkeypatch, "up3")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Soon", "mobile": "9000000010", "plan_id": plan_id})
    payments_service.mark_paid(
        conn, member_id, plan_id, _admin_id(conn),
        paid_on=datetime.date.today() - datetime.timedelta(days=28),
    )
    expected_next_start = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
    conn.close()

    at = _open(UPCOMING)
    at.button(key=f"mark_paid_{member_id}").click().run()

    assert not at.exception
    import db as db_module

    check = db_module.get_connection()
    row = check.execute(
        "SELECT period_start FROM payments WHERE member_id = ? ORDER BY id DESC LIMIT 1", (member_id,)
    ).fetchone()
    assert row["period_start"] == expected_next_start
    check.close()


def test_upcoming_page_paginates(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "up4")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    admin_id = _admin_id(conn)
    paid_on = datetime.date.today() - datetime.timedelta(days=28)
    for i in range(25):
        member_id = members_service.create_member(
            conn, {"first_name": f"Soon{i:02d}", "mobile": f"90000005{i:02d}", "plan_id": plan_id}
        )
        payments_service.mark_paid(conn, member_id, plan_id, admin_id, paid_on=paid_on)
    conn.close()

    at = _open(UPCOMING)

    assert not at.exception
    assert len([b for b in at.button if b.key and b.key.startswith("mark_paid_")]) == 20

    at.button(key="upcoming_page_next").click().run()

    assert not at.exception
    assert len([b for b in at.button if b.key and b.key.startswith("mark_paid_")]) == 5


# --- Personal Training carries across the split -------------------------

def test_mark_paid_logs_payout_when_has_pt_and_trainer_assigned(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "pt1")
    from services import members as members_service
    from services import payments as payments_service
    from services import trainers as trainers_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1000.0, 30)
    trainer_id = trainers_service.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    member_id = members_service.create_member(
        conn,
        {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id,
         "has_pt": True, "trainer_id": trainer_id},
    )
    conn.close()

    at = _open(NEVER_PAID)
    at.button(key=f"mark_paid_{member_id}").click().run()

    assert not at.exception
    assert any("Personal Training" in el.value for el in at.success)

    import db as db_module

    check = db_module.get_connection()
    assert check.execute(
        "SELECT COUNT(*) AS c FROM trainer_payments WHERE member_id = ?", (member_id,)
    ).fetchone()["c"] == 1
    assert check.execute(
        "SELECT amount FROM payments WHERE member_id = ?", (member_id,)
    ).fetchone()["amount"] == 1000.0 + 3000
    check.close()


def test_mark_paid_without_pt_says_nothing_about_training(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "pt2")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1000.0, 30)
    member_id = members_service.create_member(conn, {"first_name": "Sam", "mobile": "9000000112", "plan_id": plan_id})
    conn.close()

    at = _open(NEVER_PAID)
    at.button(key=f"mark_paid_{member_id}").click().run()

    assert not at.exception
    assert any(el.value == "Marked Sam as paid." for el in at.success)
    assert not any("Personal Training" in el.value for el in at.success)


def test_pt_member_row_names_their_trainer(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "pt3")
    from services import members as members_service
    from services import payments as payments_service
    from services import trainers as trainers_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1000.0, 30)
    trainer_id = trainers_service.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    members_service.create_member(
        conn,
        {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id,
         "has_pt": True, "trainer_id": trainer_id},
    )
    conn.close()

    at = _open(NEVER_PAID)

    assert not at.exception
    assert any("+ PT (Alex)" in el.value for el in at.markdown)


# --- date sorting -------------------------------------------------------

def _row_order(at, names):
    """Positions of each name among the rendered rows, in render order."""
    values = [el.value for el in at.markdown]
    return [n for n in sorted(names, key=lambda n: values.index(n)) if n in values]


def _seed_overdue_trio(conn):
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    admin_id = _admin_id(conn)
    today = datetime.date.today()
    # Oldest lapsed longest ago, so its due date is the earliest
    for name, days in [("Oldest", 120), ("Middle", 80), ("Newest", 40)]:
        member_id = members_service.create_member(
            conn, {"first_name": name, "mobile": f"90000{days:05d}", "plan_id": plan_id}
        )
        payments_service.mark_paid(
            conn, member_id, plan_id, admin_id, paid_on=today - datetime.timedelta(days=days)
        )
    return plan_id


def test_overdue_page_sorts_earliest_due_date_first_by_default(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "sort1")
    _seed_overdue_trio(conn)
    conn.close()

    at = _open(OVERDUE)

    assert not at.exception
    assert _row_order(at, ["Oldest", "Middle", "Newest"]) == ["Oldest", "Middle", "Newest"]


def test_overdue_page_can_sort_latest_due_date_first(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "sort2")
    _seed_overdue_trio(conn)
    conn.close()

    at = _open(OVERDUE)
    at.radio(key="overdue_page_sort").set_value("Latest first").run()

    assert not at.exception
    assert _row_order(at, ["Oldest", "Middle", "Newest"]) == ["Newest", "Middle", "Oldest"]


def test_upcoming_page_can_sort_latest_expiry_first(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "sort3")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    admin_id = _admin_id(conn)
    today = datetime.date.today()
    # paid longer ago -> expires sooner
    for name, days in [("Soonest", 30), ("Later", 27), ("Latest", 25)]:
        member_id = members_service.create_member(
            conn, {"first_name": name, "mobile": f"91000{days:05d}", "plan_id": plan_id}
        )
        payments_service.mark_paid(
            conn, member_id, plan_id, admin_id, paid_on=today - datetime.timedelta(days=days)
        )
    conn.close()

    at = _open(UPCOMING)
    assert _row_order(at, ["Soonest", "Later", "Latest"]) == ["Soonest", "Later", "Latest"]

    at.radio(key="upcoming_page_sort").set_value("Latest first").run()

    assert not at.exception
    assert _row_order(at, ["Soonest", "Later", "Latest"]) == ["Latest", "Later", "Soonest"]


def test_never_paid_page_can_sort_latest_registration_first(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "sort4")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    for i, name in enumerate(["First", "Second", "Third"]):
        members_service.create_member(
            conn, {"first_name": name, "mobile": f"9200000{i:03d}", "plan_id": plan_id}
        )
        # created_at is an ISO datetime; nudge them apart so order is defined
        conn.execute(
            "UPDATE members SET created_at = ? WHERE first_name = ?",
            (f"2026-0{i + 1}-01T09:00:00", name),
        )
    conn.commit()
    conn.close()

    at = _open(NEVER_PAID)
    assert _row_order(at, ["First", "Second", "Third"]) == ["First", "Second", "Third"]

    at.radio(key="never_paid_page_sort").set_value("Latest first").run()

    assert not at.exception
    assert _row_order(at, ["First", "Second", "Third"]) == ["Third", "Second", "First"]


def test_sort_label_names_the_pages_own_date_column(tmp_path, monkeypatch):
    conn = _fresh(tmp_path, monkeypatch, "sort5")
    _seed_overdue_trio(conn)
    conn.close()

    at = _open(OVERDUE)

    assert not at.exception
    assert at.radio(key="overdue_page_sort").label == "Sort by Due Date"


def test_changing_sort_direction_returns_to_the_first_page(tmp_path, monkeypatch):
    # otherwise you're stranded on page 3 of a list that just reversed
    conn = _fresh(tmp_path, monkeypatch, "sort6")
    from services import members as members_service
    from services import payments as payments_service

    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    admin_id = _admin_id(conn)
    today = datetime.date.today()
    for i in range(25):
        member_id = members_service.create_member(
            conn, {"first_name": f"Late{i:02d}", "mobile": f"93000006{i:02d}", "plan_id": plan_id}
        )
        payments_service.mark_paid(
            conn, member_id, plan_id, admin_id, paid_on=today - datetime.timedelta(days=40 + i)
        )
    conn.close()

    at = _open(OVERDUE)
    at.button(key="overdue_page_next").click().run()
    assert len([b for b in at.button if b.key and b.key.startswith("mark_paid_")]) == 5

    at.radio(key="overdue_page_sort").set_value("Latest first").run()

    assert not at.exception
    assert len([b for b in at.button if b.key and b.key.startswith("mark_paid_")]) == 20
