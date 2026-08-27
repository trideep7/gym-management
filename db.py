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
    mobile TEXT,
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
    has_locker INTEGER NOT NULL DEFAULT 0,
    has_pt INTEGER NOT NULL DEFAULT 0,
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
    recorded_by INTEGER NOT NULL REFERENCES users(id)
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

CREATE TABLE IF NOT EXISTS trainers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    mobile TEXT,
    time_slot TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trainer_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL REFERENCES members(id),
    trainer_id INTEGER REFERENCES trainers(id),
    amount REAL NOT NULL,
    trainer_share REAL NOT NULL,
    paid_on TEXT NOT NULL,
    recorded_by INTEGER NOT NULL REFERENCES users(id)
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
    _migrate_add_member_locker_pt_columns(conn)
    _migrate_make_member_mobile_nullable(conn)
    _migrate_add_member_trainer_id(conn)
    _migrate_make_trainer_payment_trainer_nullable(conn)
    _migrate_remove_attendance_unique_constraint(conn)
    _migrate_add_payment_period_start(conn)
    os.makedirs(get_photos_dir(), exist_ok=True)


def _migrate_add_member_plan_id(conn):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(members)")]
    if "plan_id" not in cols:
        conn.execute("ALTER TABLE members ADD COLUMN plan_id INTEGER REFERENCES membership_plans(id)")
        conn.commit()


def _migrate_add_member_locker_pt_columns(conn):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(members)")]
    if "has_locker" not in cols:
        conn.execute("ALTER TABLE members ADD COLUMN has_locker INTEGER NOT NULL DEFAULT 0")
    if "has_pt" not in cols:
        conn.execute("ALTER TABLE members ADD COLUMN has_pt INTEGER NOT NULL DEFAULT 0")
    conn.commit()


def _migrate_make_member_mobile_nullable(conn):
    # SQLite can't drop a column's NOT NULL via ALTER TABLE, so an existing
    # database (created before members without a phone number were allowed)
    # needs its members table rebuilt without that constraint. Run after the
    # plan_id/has_locker/has_pt migrations so the old table's column set
    # already matches the new schema everywhere except mobile's nullability,
    # letting the rebuild use one explicit column list for both sides.
    cols_info = list(conn.execute("PRAGMA table_info(members)"))
    mobile_col = next(c for c in cols_info if c[1] == "mobile")
    if mobile_col[3] == 0:  # notnull flag already off
        return
    col_list = ", ".join(c[1] for c in cols_info)
    # attendance/payments/payment_reminders hold a REFERENCES members(id) FK,
    # so dropping members itself (not just altering it) trips FK enforcement
    # unless it's relaxed for the duration of the rebuild.
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript(
        f"""
        CREATE TABLE members_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            surname TEXT,
            first_name TEXT NOT NULL,
            address TEXT,
            mobile TEXT,
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
            has_locker INTEGER NOT NULL DEFAULT 0,
            has_pt INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.execute(f"INSERT INTO members_new ({col_list}) SELECT {col_list} FROM members")
    conn.executescript("DROP TABLE members; ALTER TABLE members_new RENAME TO members;")
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")


def _migrate_add_member_trainer_id(conn):
    # Must run after _migrate_make_member_mobile_nullable: that migration
    # rebuilds the members table from a hardcoded column list that doesn't
    # include trainer_id, so adding this column first would make the
    # rebuild's INSERT...SELECT reference a column members_new doesn't have.
    cols = [row[1] for row in conn.execute("PRAGMA table_info(members)")]
    if "trainer_id" not in cols:
        conn.execute("ALTER TABLE members ADD COLUMN trainer_id INTEGER REFERENCES trainers(id)")
        conn.commit()


def _migrate_make_trainer_payment_trainer_nullable(conn):
    # A member can pay the PT fee before anyone has been assigned to train
    # them (every member imported from the 2026 spreadsheet is in exactly
    # that state). The fee still has to be recorded, so trainer_id has to
    # allow NULL — and SQLite can't drop NOT NULL via ALTER TABLE, so an
    # existing database needs the table rebuilt.
    cols_info = list(conn.execute("PRAGMA table_info(trainer_payments)"))
    if not cols_info:
        return
    trainer_col = next((c for c in cols_info if c[1] == "trainer_id"), None)
    if trainer_col is None or trainer_col[3] == 0:  # notnull flag already off
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript(
        """
        CREATE TABLE trainer_payments_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL REFERENCES members(id),
            trainer_id INTEGER REFERENCES trainers(id),
            amount REAL NOT NULL,
            trainer_share REAL NOT NULL,
            paid_on TEXT NOT NULL,
            recorded_by INTEGER NOT NULL REFERENCES users(id)
        );
        INSERT INTO trainer_payments_new (id, member_id, trainer_id, amount, trainer_share, paid_on, recorded_by)
            SELECT id, member_id, trainer_id, amount, trainer_share, paid_on, recorded_by FROM trainer_payments;
        DROP TABLE trainer_payments;
        ALTER TABLE trainer_payments_new RENAME TO trainer_payments;
        """
    )
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")


def _migrate_remove_attendance_unique_constraint(conn):
    # SQLite can't drop a table constraint via ALTER TABLE, so an existing
    # database (created before members could sign in more than once a day)
    # needs its attendance table rebuilt without it.
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='attendance'"
    ).fetchone()
    if row and "UNIQUE" in row["sql"].upper():
        conn.executescript(
            """
            CREATE TABLE attendance_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL REFERENCES members(id),
                sign_in_date TEXT NOT NULL,
                sign_in_time TEXT NOT NULL,
                recorded_by INTEGER NOT NULL REFERENCES users(id)
            );
            INSERT INTO attendance_new (id, member_id, sign_in_date, sign_in_time, recorded_by)
                SELECT id, member_id, sign_in_date, sign_in_time, recorded_by FROM attendance;
            DROP TABLE attendance;
            ALTER TABLE attendance_new RENAME TO attendance;
            """
        )
        conn.commit()


def _migrate_add_payment_period_start(conn):
    # Payments recorded before billing periods were tracked only stored
    # valid_until. Reconstruct the period they covered by working back from
    # the plan's duration -- that's exactly what the old
    # valid_until = paid_on + duration_days formula implied, so historical
    # rows keep rendering the dates they always effectively had.
    cols = [row[1] for row in conn.execute("PRAGMA table_info(payments)")]
    if "period_start" in cols:
        return
    conn.execute("ALTER TABLE payments ADD COLUMN period_start TEXT")
    # A payment whose plan row was hard-deleted has no duration to work back
    # from; the subquery yields NULL there and date(NULL) leaves it NULL
    # rather than inventing a date.
    conn.execute(
        "UPDATE payments SET period_start = date("
        "  valid_until,"
        "  '-' || (SELECT duration_days FROM membership_plans WHERE id = payments.plan_id) || ' days'"
        ") WHERE period_start IS NULL"
    )
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
