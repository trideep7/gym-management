def login_as_admin(at):
    at.text_input(key="login_username").input("admin").run()
    at.text_input(key="login_password").input("password").run()
    at.button(key="login_button").click().run()
    return at


def test_help_page_renders_all_sections(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos"))

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../app.py")
    at.run()
    login_as_admin(at)
    at.switch_page("pages_/help.py")
    at.run()

    assert not at.exception
    expander_labels = [e.label for e in at.expander]
    assert expander_labels == [
        "Signing In Members (Dashboard)",
        "Members — Add, Edit, View, Search",
        "Payments — Plans, Marking Paid, Reminders",
        "Reminder Message Templates",
        "Equipment — Inventory",
        "Reports",
        "Common Issues",
    ]
    assert any("10 digits" in el.value for el in at.markdown)
    assert any("Upcoming Renewal" in el.value for el in at.markdown)
    assert any("Overdue Payment" in el.value for el in at.markdown)
    assert any("Reactivating a member" in el.value for el in at.markdown)
    assert any("Active Members" in el.value for el in at.markdown)
