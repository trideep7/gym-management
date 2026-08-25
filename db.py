import datetime
import os
import sqlite3

import bcrypt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin','staff')),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    surname TEXT,
    first_name TEXT NOT NULL,
    address TEXT,
    mobile TEXT NOT NULL,
    email TEXT,
    instagram_id TEXT,
    occupation TEXT,
    is_student INTEGER NOT NULL DEFAULT 0,
    school_college_name TEXT,
    grade_semester TEXT,
    dob TEXT,
    gender TEXT,
    how_found_us TEXT,
    photo_path TEXT,
    preferred_time_slot TEXT,
    med_heart_disease INTEGER NOT NULL DEFAULT 0,
    med_dizziness INTEGER NOT NULL DEFAULT 0,
    med_blackouts INTEGER NOT NULL DEFAULT 0,
    med_asthma INTEGER NOT NULL DEFAULT 0,
    med_high_low_bp INTEGER NOT NULL DEFAULT 0,
    med_diabetes INTEGER NOT NULL DEFAULT 0,
    med_gout INTEGER NOT NULL DEFAULT 0,
    med_other_condition TEXT,
    injury_knees INTEGER NOT NULL DEFAULT 0,
    injury_lower_back INTEGER NOT NULL DEFAULT 0,
    injury_neck_shoulder INTEGER NOT NULL DEFAULT 0,
    injury_hips_pelvic INTEGER NOT NULL DEFAULT 0,
    injury_other TEXT,
    surgery_details TEXT,
    medication_details TEXT,
    additional_notes TEXT,
    plan_id INTEGER REFERENCES membership_plans(id),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS membership_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    amount REAL NOT NULL,
    duration_days INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL REFERENCES members(id),
    plan_id INTEGER NOT NULL REFERENCES membership_plans(id),
    amount REAL NOT NULL,
    paid_on TEXT NOT NULL,
    valid_until TEXT NOT NULL,
    recorded_by INTEGER NOT NULL REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS payment_reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL REFERENCES members(id),
    sent_by INTEGER NOT NULL REFERENCES users(id),
    sent_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL REFERENCES members(id),
    sign_in_date TEXT NOT NULL,
    sign_in_time TEXT NOT NULL,
    recorded_by INTEGER NOT NULL REFERENCES users(id),
    UNIQUE(member_id, sign_in_date)
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    updated_at TEXT NOT NULL
);
"""


def get_db_path():
    return os.environ.get("GYM_DB_PATH", os.path.join(DATA_DIR, "gym.db"))


def get_photos_dir():
    return os.environ.get("GYM_PHOTOS_DIR", os.path.join(DATA_DIR, "photos"))


def get_connection(db_path=None):
    path = db_path or get_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # check_same_thread=False: st.dialog/st.fragment callbacks run on a
    # different thread than the main script, and this connection is created
    # once at the top of each page and closed over by any dialog on it.
    # SQLite itself is safe for this (serialized threading mode); we're only
    # disabling Python's same-thread guard, not concurrent-write safety,
    # which was never guaranteed by a single shared connection anyway.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn):
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate_add_member_plan_id(conn)
    os.makedirs(get_photos_dir(), exist_ok=True)


def _migrate_add_member_plan_id(conn):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(members)")]
    if "plan_id" not in cols:
        conn.execute("ALTER TABLE members ADD COLUMN plan_id INTEGER REFERENCES membership_plans(id)")
        conn.commit()


def seed_admin(conn):
    row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
    if row["c"] == 0:
        password_hash = bcrypt.hashpw(b"password", bcrypt.gensalt()).decode("utf-8")
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role, is_active, created_at) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            ("admin", password_hash, "Administrator", "admin", datetime.datetime.now().isoformat()),
        )
        conn.commit()
