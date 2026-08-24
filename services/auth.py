import datetime
import secrets

import bcrypt


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, password_hash):
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def authenticate(conn, username, password):
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? AND is_active = 1", (username,)
    ).fetchone()
    if row is None:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "full_name": row["full_name"],
        "role": row["role"],
    }


def create_session(conn, user_id):
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, user_id, datetime.datetime.now().isoformat()),
    )
    conn.commit()
    return token


def get_session_user(conn, token):
    row = conn.execute(
        "SELECT users.* FROM sessions JOIN users ON sessions.user_id = users.id "
        "WHERE sessions.token = ? AND users.is_active = 1",
        (token,),
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "full_name": row["full_name"],
        "role": row["role"],
    }


def delete_session(conn, token):
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()


def create_user(conn, username, password, full_name, role="staff"):
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        raise ValueError(f"Username '{username}' is already taken")
    cursor = conn.execute(
        "INSERT INTO users (username, password_hash, full_name, role, is_active, created_at) "
        "VALUES (?, ?, ?, ?, 1, ?)",
        (username, hash_password(password), full_name, role, datetime.datetime.now().isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def list_users(conn):
    rows = conn.execute(
        "SELECT id, username, full_name, role, is_active, created_at FROM users ORDER BY username"
    ).fetchall()
    return [dict(r) for r in rows]


def set_user_active(conn, user_id, is_active):
    conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (1 if is_active else 0, user_id))
    conn.commit()


def reset_password(conn, user_id, new_password):
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new_password), user_id)
    )
    conn.commit()
