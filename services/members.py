import datetime
import os
import re

REQUIRED_FIELDS = ("first_name", "plan_id")
MOBILE_PATTERN = re.compile(r"^[1-9]\d{9}$")

BOOLEAN_COLUMNS = {
    "is_student", "med_heart_disease", "med_dizziness", "med_blackouts", "med_asthma",
    "med_high_low_bp", "med_diabetes", "med_gout", "injury_knees", "injury_lower_back",
    "injury_neck_shoulder", "injury_hips_pelvic", "has_locker", "has_pt",
}

COLUMNS = [
    "surname", "first_name", "address", "mobile", "email", "instagram_id",
    "occupation", "is_student", "school_college_name", "grade_semester",
    "dob", "gender", "how_found_us", "photo_path", "preferred_time_slot",
    "med_heart_disease", "med_dizziness", "med_blackouts", "med_asthma",
    "med_high_low_bp", "med_diabetes", "med_gout", "med_other_condition",
    "injury_knees", "injury_lower_back", "injury_neck_shoulder",
    "injury_hips_pelvic", "injury_other", "surgery_details",
    "medication_details", "additional_notes", "plan_id", "has_locker", "has_pt", "trainer_id",
]


def _normalize_mobile(value):
    """Blank/whitespace-only input means "no phone on file" — store that as
    NULL, never as an empty string, so the two can't both mean the same
    thing in the DB (the Dashboard's no-phone branch keys off NULL)."""
    if value is None:
        return None
    trimmed = str(value).strip()
    return trimmed or None


def _validate(data):
    for field in REQUIRED_FIELDS:
        if not data.get(field):
            raise ValueError(f"{field} is required")
    mobile = _normalize_mobile(data.get("mobile"))
    if mobile and not MOBILE_PATTERN.match(mobile):
        raise ValueError("Mobile number must be exactly 10 digits and cannot start with 0")


def _column_value(col, data):
    value = data.get(col)
    if col in BOOLEAN_COLUMNS:
        return 1 if value else 0
    if col == "mobile":
        return _normalize_mobile(value)
    return value


def create_member(conn, data):
    _validate(data)
    values = [_column_value(col, data) for col in COLUMNS]
    placeholders = ", ".join(["?"] * len(COLUMNS))
    cursor = conn.execute(
        f"INSERT INTO members ({', '.join(COLUMNS)}, is_active, created_at) "
        f"VALUES ({placeholders}, 1, ?)",
        values + [datetime.datetime.now().isoformat()],
    )
    conn.commit()
    return cursor.lastrowid


def update_member(conn, member_id, data):
    _validate(data)
    assignments = ", ".join(f"{col} = ?" for col in COLUMNS)
    values = [_column_value(col, data) for col in COLUMNS]
    conn.execute(f"UPDATE members SET {assignments} WHERE id = ?", values + [member_id])
    conn.commit()


def get_member(conn, member_id):
    row = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    return dict(row) if row else None


def search_members(conn, query="", active_only=True):
    sql = "SELECT * FROM members WHERE (first_name LIKE ? OR surname LIKE ? OR mobile LIKE ?)"
    params = [f"%{query}%", f"%{query}%", f"%{query}%"]
    if active_only:
        sql += " AND is_active = 1"
    sql += " ORDER BY first_name"
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def find_by_mobile(conn, mobile):
    rows = conn.execute(
        "SELECT * FROM members WHERE mobile = ? AND is_active = 1", (mobile,)
    ).fetchall()
    return [dict(r) for r in rows]


def set_member_active(conn, member_id, is_active):
    conn.execute("UPDATE members SET is_active = ? WHERE id = ?", (1 if is_active else 0, member_id))
    conn.commit()


ALLOWED_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png"}


def save_photo(photo_bytes, member_id, ext, photos_dir):
    normalized_ext = ext.lstrip(".").lower()
    if normalized_ext not in ALLOWED_PHOTO_EXTENSIONS:
        raise ValueError(f"Unsupported photo file type: '{ext}'. Use JPG or PNG.")
    os.makedirs(photos_dir, exist_ok=True)
    filename = f"member_{member_id}.{normalized_ext}"
    with open(os.path.join(photos_dir, filename), "wb") as f:
        f.write(photo_bytes)
    return filename
