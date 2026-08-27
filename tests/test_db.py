import db as db_module


def test_init_db_creates_all_tables(conn):
    tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    expected = {
        "users", "members", "membership_plans", "payments", "attendance",
        "equipment", "payment_reminders",
    }
    assert expected <= tables


def test_seed_admin_creates_default_user(conn):
    db_module.seed_admin(conn)
    row = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
    assert row is not None
    assert row["role"] == "admin"
    assert row["is_active"] == 1


def test_seed_admin_is_idempotent(conn):
    db_module.seed_admin(conn)
    db_module.seed_admin(conn)
    count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    assert count == 1


def test_get_connection_enables_foreign_keys(conn):
    row = conn.execute("PRAGMA foreign_keys").fetchone()
    assert row[0] == 1


def test_init_db_creates_plan_id_column_on_members(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(members)")]
    assert "plan_id" in cols


def test_init_db_migrates_existing_members_table_without_plan_id(tmp_path):
    # simulate a pre-existing database created before plan_id existed
    db_path = str(tmp_path / "old_gym.db")
    old_conn = db_module.get_connection(db_path)
    old_conn.executescript(
        """
        CREATE TABLE members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        """
    )
    old_conn.execute(
        "INSERT INTO members (first_name, mobile, is_active, created_at) VALUES (?, ?, 1, ?)",
        ("Sam", "111", "2026-01-01T00:00:00"),
    )
    old_conn.commit()
    old_conn.close()

    upgraded_conn = db_module.get_connection(db_path)
    db_module.init_db(upgraded_conn)

    cols = [r[1] for r in upgraded_conn.execute("PRAGMA table_info(members)")]
    assert "plan_id" in cols
    row = upgraded_conn.execute("SELECT first_name, plan_id FROM members WHERE first_name = 'Sam'").fetchone()
    assert row["first_name"] == "Sam"
    assert row["plan_id"] is None


def test_init_db_creates_locker_and_pt_columns_on_members(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(members)")]
    assert "has_locker" in cols
    assert "has_pt" in cols


def test_init_db_migrates_existing_members_table_without_locker_pt_columns(tmp_path):
    db_path = str(tmp_path / "old_gym.db")
    old_conn = db_module.get_connection(db_path)
    old_conn.executescript(
        """
        CREATE TABLE members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        """
    )
    old_conn.execute(
        "INSERT INTO members (first_name, mobile, is_active, created_at) VALUES (?, ?, 1, ?)",
        ("Sam", "9000000111", "2026-01-01T00:00:00"),
    )
    old_conn.commit()
    old_conn.close()

    upgraded_conn = db_module.get_connection(db_path)
    db_module.init_db(upgraded_conn)

    row = upgraded_conn.execute("SELECT has_locker, has_pt FROM members WHERE first_name = 'Sam'").fetchone()
    assert row["has_locker"] == 0
    assert row["has_pt"] == 0


def test_init_db_allows_null_mobile_on_members(conn):
    cols_info = list(conn.execute("PRAGMA table_info(members)"))
    mobile_col = next(c for c in cols_info if c[1] == "mobile")
    assert mobile_col[3] == 0  # notnull flag off
    conn.execute(
        "INSERT INTO members (first_name, mobile, is_active, created_at) VALUES ('Riley', NULL, 1, '2026-01-01T00:00:00')"
    )
    row = conn.execute("SELECT mobile FROM members WHERE first_name = 'Riley'").fetchone()
    assert row["mobile"] is None


def test_init_db_migrates_existing_members_table_with_mobile_not_null(tmp_path):
    # simulate a pre-existing database created before members without a phone
    # number were allowed
    db_path = str(tmp_path / "old_gym.db")
    old_conn = db_module.get_connection(db_path)
    old_conn.executescript(
        """
        CREATE TABLE members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        """
    )
    old_conn.execute(
        "INSERT INTO members (first_name, mobile, is_active, created_at) VALUES (?, ?, 1, ?)",
        ("Sam", "9000000111", "2026-01-01T00:00:00"),
    )
    old_conn.commit()
    old_conn.close()

    upgraded_conn = db_module.get_connection(db_path)
    db_module.init_db(upgraded_conn)

    cols_info = list(upgraded_conn.execute("PRAGMA table_info(members)"))
    mobile_col = next(c for c in cols_info if c[1] == "mobile")
    assert mobile_col[3] == 0

    # the existing row must survive the migration
    row = upgraded_conn.execute("SELECT first_name, mobile FROM members WHERE first_name = 'Sam'").fetchone()
    assert row["mobile"] == "9000000111"

    # and a member with no phone number must now be insertable
    upgraded_conn.execute(
        "INSERT INTO members (first_name, mobile, is_active, created_at) VALUES ('Riley', NULL, 1, '2026-01-01T00:00:00')"
    )
    row = upgraded_conn.execute("SELECT mobile FROM members WHERE first_name = 'Riley'").fetchone()
    assert row["mobile"] is None


def test_payment_reminders_table_has_expected_columns(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(payment_reminders)")}
    assert cols == {"id", "member_id", "sent_by", "sent_at"}


def test_attendance_table_allows_multiple_signins_same_day(conn):
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='attendance'"
    ).fetchone()[0]
    assert "UNIQUE" not in sql.upper()


def test_init_db_migrates_existing_attendance_table_with_unique_constraint(tmp_path):
    # simulate a pre-existing database created before the constraint was removed
    db_path = str(tmp_path / "old_gym.db")
    old_conn = db_module.get_connection(db_path)
    old_conn.executescript(
        """
        CREATE TABLE members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL REFERENCES members(id),
            sign_in_date TEXT NOT NULL,
            sign_in_time TEXT NOT NULL,
            recorded_by INTEGER NOT NULL REFERENCES users(id),
            UNIQUE(member_id, sign_in_date)
        );
        """
    )
    old_conn.execute(
        "INSERT INTO members (first_name, mobile, is_active, created_at) VALUES (?, ?, 1, ?)",
        ("Sam", "9000000111", "2026-01-01T00:00:00"),
    )
    old_conn.execute(
        "INSERT INTO users (username, password_hash, full_name, role, is_active, created_at) "
        "VALUES ('staffer', 'hash', 'Staff One', 'staff', 1, '2026-01-01T00:00:00')"
    )
    old_conn.execute(
        "INSERT INTO attendance (member_id, sign_in_date, sign_in_time, recorded_by) VALUES (1, '2026-01-01', '09:00:00', 1)"
    )
    old_conn.commit()
    old_conn.close()

    upgraded_conn = db_module.get_connection(db_path)
    db_module.init_db(upgraded_conn)

    sql = upgraded_conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='attendance'"
    ).fetchone()[0]
    assert "UNIQUE" not in sql.upper()
    # the existing row must survive the migration
    row = upgraded_conn.execute("SELECT * FROM attendance WHERE member_id = 1").fetchone()
    assert row["sign_in_date"] == "2026-01-01"
    # and a same-day second sign-in must now be insertable
    upgraded_conn.execute(
        "INSERT INTO attendance (member_id, sign_in_date, sign_in_time, recorded_by) VALUES (1, '2026-01-01', '17:00:00', 1)"
    )
    upgraded_conn.commit()
    count = upgraded_conn.execute("SELECT COUNT(*) AS c FROM attendance WHERE member_id = 1").fetchone()["c"]
    assert count == 2


def test_init_db_creates_trainer_tables(conn):
    tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"trainers", "trainer_payments"} <= tables


def test_init_db_creates_trainer_id_column_on_members(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(members)")]
    assert "trainer_id" in cols


def test_init_db_migrates_existing_members_table_without_trainer_id(tmp_path):
    db_path = str(tmp_path / "old_gym.db")
    old_conn = db_module.get_connection(db_path)
    old_conn.executescript(
        """
        CREATE TABLE members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            mobile TEXT,
            plan_id INTEGER,
            has_locker INTEGER NOT NULL DEFAULT 0,
            has_pt INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        """
    )
    old_conn.execute(
        "INSERT INTO members (first_name, mobile, is_active, created_at) VALUES (?, ?, 1, ?)",
        ("Sam", "9000000111", "2026-01-01T00:00:00"),
    )
    old_conn.commit()
    old_conn.close()

    upgraded_conn = db_module.get_connection(db_path)
    db_module.init_db(upgraded_conn)

    cols = [r[1] for r in upgraded_conn.execute("PRAGMA table_info(members)")]
    assert "trainer_id" in cols
    row = upgraded_conn.execute("SELECT first_name, trainer_id FROM members WHERE first_name = 'Sam'").fetchone()
    assert row["trainer_id"] is None


def test_trainer_payments_table_has_expected_columns(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(trainer_payments)")}
    assert cols == {"id", "member_id", "trainer_id", "amount", "trainer_share", "paid_on", "recorded_by"}


def test_trainer_payments_allows_null_trainer_id(conn):
    cols_info = list(conn.execute("PRAGMA table_info(trainer_payments)"))
    trainer_col = next(c for c in cols_info if c[1] == "trainer_id")
    assert trainer_col[3] == 0  # notnull flag off


def test_init_db_migrates_trainer_payments_with_not_null_trainer_id(tmp_path):
    # a database created before PT fees could be recorded without an
    # assigned trainer needs its trainer_payments table rebuilt
    db_path = str(tmp_path / "old_gym.db")
    old_conn = db_module.get_connection(db_path)
    old_conn.executescript(
        """
        CREATE TABLE members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            mobile TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE trainers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT,
            time_slot TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE trainer_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL REFERENCES members(id),
            trainer_id INTEGER NOT NULL REFERENCES trainers(id),
            amount REAL NOT NULL,
            trainer_share REAL NOT NULL,
            paid_on TEXT NOT NULL,
            recorded_by INTEGER NOT NULL REFERENCES users(id)
        );
        INSERT INTO members (first_name, mobile, is_active, created_at)
            VALUES ('Sam', '9000000111', 1, '2026-01-01T00:00:00');
        INSERT INTO users (username, password_hash, full_name, role, is_active, created_at)
            VALUES ('staffer', 'hash', 'Staff One', 'staff', 1, '2026-01-01T00:00:00');
        INSERT INTO trainers (name, mobile, time_slot, is_active, created_at)
            VALUES ('Alex', '9000000001', '6-8 AM', 1, '2026-01-01T00:00:00');
        INSERT INTO trainer_payments (member_id, trainer_id, amount, trainer_share, paid_on, recorded_by)
            VALUES (1, 1, 3000, 2000, '2026-08-01', 1);
        """
    )
    old_conn.commit()
    old_conn.close()

    upgraded_conn = db_module.get_connection(db_path)
    db_module.init_db(upgraded_conn)

    cols_info = list(upgraded_conn.execute("PRAGMA table_info(trainer_payments)"))
    trainer_col = next(c for c in cols_info if c[1] == "trainer_id")
    assert trainer_col[3] == 0

    # the existing attributed row must survive
    row = upgraded_conn.execute("SELECT * FROM trainer_payments WHERE id = 1").fetchone()
    assert row["trainer_id"] == 1
    assert row["amount"] == 3000

    # and an unattributed payout must now be insertable
    upgraded_conn.execute(
        "INSERT INTO trainer_payments (member_id, trainer_id, amount, trainer_share, paid_on, recorded_by) "
        "VALUES (1, NULL, 3000, 2000, '2026-09-01', 1)"
    )
    upgraded_conn.commit()
    assert upgraded_conn.execute(
        "SELECT COUNT(*) AS c FROM trainer_payments WHERE trainer_id IS NULL"
    ).fetchone()["c"] == 1


def test_init_db_creates_settings_table(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(settings)")}
    assert cols == {"key", "value"}


def test_init_db_creates_period_start_column_on_payments(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(payments)")]
    assert "period_start" in cols


def test_init_db_backfills_period_start_on_existing_payments(tmp_path):
    # a payment recorded before periods were tracked only knows valid_until,
    # so the migration reconstructs the period it would have covered under
    # the old paid_on + duration_days formula
    db_path = str(tmp_path / "old_gym.db")
    old_conn = db_module.get_connection(db_path)
    old_conn.executescript(
        """
        CREATE TABLE membership_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            duration_days INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            paid_on TEXT NOT NULL,
            valid_until TEXT NOT NULL,
            recorded_by INTEGER NOT NULL
        );
        INSERT INTO membership_plans (id, name, amount, duration_days) VALUES (1, 'Monthly', 1500.0, 30);
        INSERT INTO payments (member_id, plan_id, amount, paid_on, valid_until, recorded_by)
            VALUES (1, 1, 1500.0, '2026-01-15', '2026-02-14', 1);
        """
    )
    old_conn.commit()
    old_conn.close()

    upgraded_conn = db_module.get_connection(db_path)
    db_module.init_db(upgraded_conn)

    row = upgraded_conn.execute("SELECT period_start, valid_until FROM payments").fetchone()
    assert row["period_start"] == "2026-01-15"
    assert row["valid_until"] == "2026-02-14"


def test_init_db_leaves_period_start_null_when_plan_is_missing(tmp_path):
    # a payment whose plan row was hard-deleted has no duration to work
    # back from; the migration must not crash or invent a date
    db_path = str(tmp_path / "orphan_gym.db")
    old_conn = db_module.get_connection(db_path)
    old_conn.executescript(
        """
        CREATE TABLE payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            paid_on TEXT NOT NULL,
            valid_until TEXT NOT NULL,
            recorded_by INTEGER NOT NULL
        );
        INSERT INTO payments (member_id, plan_id, amount, paid_on, valid_until, recorded_by)
            VALUES (1, 999, 1500.0, '2026-01-15', '2026-02-14', 1);
        """
    )
    old_conn.commit()
    old_conn.close()

    upgraded_conn = db_module.get_connection(db_path)
    db_module.init_db(upgraded_conn)

    row = upgraded_conn.execute("SELECT period_start FROM payments").fetchone()
    assert row["period_start"] is None
