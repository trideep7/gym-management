import pytest

from services import members as members_service
from services import payments as payments_service
from services import settings as settings_service


def _member(conn, name, plan_id, **extra):
    return members_service.create_member(
        conn, {"first_name": name, "plan_id": plan_id, **extra}
    )


def test_get_setting_returns_default_when_unset(conn):
    assert settings_service.get_setting(conn, "nothing_here", "fallback") == "fallback"


def test_set_setting_then_get_setting_round_trips(conn):
    settings_service.set_setting(conn, "greeting", "hello")
    assert settings_service.get_setting(conn, "greeting") == "hello"


def test_set_setting_overwrites_existing_value(conn):
    settings_service.set_setting(conn, "greeting", "hello")
    settings_service.set_setting(conn, "greeting", "goodbye")
    assert settings_service.get_setting(conn, "greeting") == "goodbye"


def test_get_int_setting_returns_stored_number(conn):
    settings_service.set_setting(conn, "locker_count", "40")
    assert settings_service.get_int_setting(conn, "locker_count", 0) == 40


def test_get_int_setting_falls_back_when_value_is_not_a_number(conn):
    # hand-edited databases shouldn't crash the app on every page load
    settings_service.set_setting(conn, "locker_count", "forty")
    assert settings_service.get_int_setting(conn, "locker_count", 0) == 0


def test_locker_count_defaults_to_zero_meaning_no_limit_set(conn):
    assert settings_service.get_locker_count(conn) == 0


def test_set_locker_count_persists(conn):
    settings_service.set_locker_count(conn, 40)
    assert settings_service.get_locker_count(conn) == 40


def test_set_locker_count_rejects_a_negative_total(conn):
    with pytest.raises(ValueError):
        settings_service.set_locker_count(conn, -1)


def test_lockers_in_use_counts_members_holding_one(conn):
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    _member(conn, "Asha", plan_id, has_locker=True)
    _member(conn, "Ravi", plan_id, has_locker=True)
    _member(conn, "Neha", plan_id, has_locker=False)
    assert settings_service.lockers_in_use(conn) == 2


def test_lockers_in_use_ignores_inactive_members(conn):
    # a deactivated member isn't occupying a locker any more
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    _member(conn, "Asha", plan_id, has_locker=True)
    gone = _member(conn, "Ravi", plan_id, has_locker=True)
    members_service.set_member_active(conn, gone, False)
    assert settings_service.lockers_in_use(conn) == 1


def test_lockers_in_use_can_exclude_one_member(conn):
    # editing a member who already holds a locker must not count them
    # against the total and block their own save
    plan_id = payments_service.create_plan(conn, "Monthly", 1500.0, 30)
    asha = _member(conn, "Asha", plan_id, has_locker=True)
    _member(conn, "Ravi", plan_id, has_locker=True)
    assert settings_service.lockers_in_use(conn, exclude_member_id=asha) == 1


def test_renewal_grace_days_defaults_to_seven(conn):
    assert settings_service.get_renewal_grace_days(conn) == 7


def test_set_renewal_grace_days_persists(conn):
    settings_service.set_renewal_grace_days(conn, 3)
    assert settings_service.get_renewal_grace_days(conn) == 3


def test_set_renewal_grace_days_rejects_a_negative_window(conn):
    with pytest.raises(ValueError):
        settings_service.set_renewal_grace_days(conn, -1)
