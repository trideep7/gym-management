"""Admin-managed timing options, shared by the member and trainer forms.

Stored as a single JSON list under the "time_slots" key in the generic
settings table rather than a dedicated table -- there's no foreign key
from members/trainers to a slot (their own column is plain text), so a
slot has no relational identity worth a table of its own.
"""

import json

from services import settings as settings_service

SETTINGS_KEY = "time_slots"


def _load(conn):
    raw = settings_service.get_setting(conn, SETTINGS_KEY)
    if raw is None:
        return []
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return []


def _save(conn, slots):
    settings_service.set_setting(conn, SETTINGS_KEY, json.dumps(slots))


def _get(slots, slot_id):
    slot = next((s for s in slots if s["id"] == slot_id), None)
    if slot is None:
        raise ValueError(f"No timing option with id {slot_id}")
    return slot


def list_time_slots(conn, active_only=True):
    slots = _load(conn)
    if active_only:
        slots = [s for s in slots if s["is_active"]]
    return slots


def create_time_slot(conn, label):
    label = (label or "").strip()
    if not label:
        raise ValueError("Timing option is required.")
    slots = _load(conn)
    next_id = max((s["id"] for s in slots), default=0) + 1
    slots.append({"id": next_id, "label": label, "is_active": True})
    _save(conn, slots)
    return next_id


def update_time_slot(conn, slot_id, label):
    label = (label or "").strip()
    if not label:
        raise ValueError("Timing option is required.")
    slots = _load(conn)
    slot = _get(slots, slot_id)
    slot["label"] = label
    _save(conn, slots)


def set_time_slot_active(conn, slot_id, is_active):
    slots = _load(conn)
    slot = _get(slots, slot_id)
    slot["is_active"] = bool(is_active)
    _save(conn, slots)


def _is_referenced(conn, label):
    member_count = conn.execute(
        "SELECT COUNT(*) AS c FROM members WHERE preferred_time_slot = ?", (label,)
    ).fetchone()["c"]
    trainer_count = conn.execute(
        "SELECT COUNT(*) AS c FROM trainers WHERE time_slot = ?", (label,)
    ).fetchone()["c"]
    return member_count > 0 or trainer_count > 0


def delete_time_slot(conn, slot_id):
    slots = _load(conn)
    slot = _get(slots, slot_id)
    if _is_referenced(conn, slot["label"]):
        slot["is_active"] = False
        _save(conn, slots)
        return "deactivated"
    slots = [s for s in slots if s["id"] != slot_id]
    _save(conn, slots)
    return "deleted"
