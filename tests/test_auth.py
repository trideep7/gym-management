import pytest

from services import auth


def test_hash_and_verify_password_roundtrip():
    hashed = auth.hash_password("secret123")
    assert auth.verify_password("secret123", hashed)
    assert not auth.verify_password("wrong", hashed)


def test_authenticate_success_after_seed(conn):
    import db as db_module

    db_module.seed_admin(conn)
    user = auth.authenticate(conn, "admin", "password")
    assert user is not None
    assert user["role"] == "admin"
    assert user["username"] == "admin"


def test_authenticate_wrong_password_returns_none(conn):
    import db as db_module

    db_module.seed_admin(conn)
    assert auth.authenticate(conn, "admin", "wrongpass") is None


def test_authenticate_unknown_user_returns_none(conn):
    assert auth.authenticate(conn, "nobody", "password") is None


def test_authenticate_inactive_user_returns_none(conn):
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    auth.set_user_active(conn, user_id, False)
    assert auth.authenticate(conn, "staffer", "pw12345") is None


def test_create_user_duplicate_username_raises(conn):
    auth.create_user(conn, "dupe", "pw12345", "First", "staff")
    with pytest.raises(ValueError):
        auth.create_user(conn, "dupe", "pw12345", "Second", "staff")


def test_reset_password_changes_credential(conn):
    user_id = auth.create_user(conn, "resetme", "oldpass1", "Reset Me", "staff")
    auth.reset_password(conn, user_id, "newpass1")
    assert auth.authenticate(conn, "resetme", "newpass1") is not None
    assert auth.authenticate(conn, "resetme", "oldpass1") is None


def test_list_users_returns_created_users(conn):
    auth.create_user(conn, "listme", "pw12345", "List Me", "staff")
    usernames = {u["username"] for u in auth.list_users(conn)}
    assert "listme" in usernames
