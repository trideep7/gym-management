import datetime


def create_equipment(conn, name, quantity, notes=""):
    cursor = conn.execute(
        "INSERT INTO equipment (name, quantity, notes, updated_at) VALUES (?, ?, ?, ?)",
        (name, quantity, notes, datetime.datetime.now().isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def update_equipment(conn, equipment_id, name, quantity, notes):
    conn.execute(
        "UPDATE equipment SET name = ?, quantity = ?, notes = ?, updated_at = ? WHERE id = ?",
        (name, quantity, notes, datetime.datetime.now().isoformat(), equipment_id),
    )
    conn.commit()


def delete_equipment(conn, equipment_id):
    conn.execute("DELETE FROM equipment WHERE id = ?", (equipment_id,))
    conn.commit()


def list_equipment(conn):
    rows = conn.execute("SELECT * FROM equipment ORDER BY name").fetchall()
    return [dict(r) for r in rows]
