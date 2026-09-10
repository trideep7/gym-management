from services import members, payments, time_slots, trainers


def test_list_time_slots_is_empty_before_anything_is_added(conn):
    assert time_slots.list_time_slots(conn) == []


def test_create_time_slot_adds_it_active(conn):
    slot_id = time_slots.create_time_slot(conn, "6:00 AM - 8:00 AM")
    listed = time_slots.list_time_slots(conn)
    assert len(listed) == 1
    assert listed[0]["id"] == slot_id
    assert listed[0]["label"] == "6:00 AM - 8:00 AM"
    assert listed[0]["is_active"] is True


def test_create_time_slot_rejects_a_blank_label(conn):
    import pytest

    with pytest.raises(ValueError):
        time_slots.create_time_slot(conn, "   ")


def test_created_ids_are_assigned_in_order_and_stay_stable(conn):
    first_id = time_slots.create_time_slot(conn, "Morning")
    second_id = time_slots.create_time_slot(conn, "Evening")
    assert second_id != first_id
    labels_by_id = {s["id"]: s["label"] for s in time_slots.list_time_slots(conn)}
    assert labels_by_id[first_id] == "Morning"
    assert labels_by_id[second_id] == "Evening"


def test_update_time_slot_changes_the_label(conn):
    slot_id = time_slots.create_time_slot(conn, "Morning")
    time_slots.update_time_slot(conn, slot_id, "Early Morning")
    assert time_slots.list_time_slots(conn)[0]["label"] == "Early Morning"


def test_update_time_slot_rejects_a_blank_label(conn):
    import pytest

    slot_id = time_slots.create_time_slot(conn, "Morning")
    with pytest.raises(ValueError):
        time_slots.update_time_slot(conn, slot_id, "")


def test_update_time_slot_rejects_an_unknown_id(conn):
    import pytest

    with pytest.raises(ValueError):
        time_slots.update_time_slot(conn, 9999, "Morning")


def test_set_time_slot_active_hides_from_default_list(conn):
    slot_id = time_slots.create_time_slot(conn, "Morning")
    time_slots.set_time_slot_active(conn, slot_id, False)
    assert time_slots.list_time_slots(conn) == []
    all_slots = time_slots.list_time_slots(conn, active_only=False)
    assert all_slots[0]["is_active"] is False


def test_delete_time_slot_removes_an_unused_one_completely(conn):
    slot_id = time_slots.create_time_slot(conn, "Morning")
    result = time_slots.delete_time_slot(conn, slot_id)
    assert result == "deleted"
    assert time_slots.list_time_slots(conn, active_only=False) == []


def test_delete_time_slot_rejects_an_unknown_id(conn):
    import pytest

    with pytest.raises(ValueError):
        time_slots.delete_time_slot(conn, 9999)


def test_delete_time_slot_deactivates_when_a_member_has_it(conn):
    slot_id = time_slots.create_time_slot(conn, "Morning")
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    members.create_member(
        conn,
        {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id, "preferred_time_slot": "Morning"},
    )

    result = time_slots.delete_time_slot(conn, slot_id)

    assert result == "deactivated"
    all_slots = time_slots.list_time_slots(conn, active_only=False)
    assert all_slots[0]["is_active"] is False


def test_delete_time_slot_deactivates_when_a_trainer_has_it(conn):
    slot_id = time_slots.create_time_slot(conn, "Morning")
    trainers.create_trainer(conn, "Alex", "9000000001", "Morning")

    result = time_slots.delete_time_slot(conn, slot_id)

    assert result == "deactivated"


def test_deactivating_a_slot_does_not_change_a_members_existing_selection(conn):
    # the option list is a curated suggestion, not a foreign key -- a
    # member's own stored text is never rewritten by admin changes to the
    # canonical list
    slot_id = time_slots.create_time_slot(conn, "Morning")
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    member_id = members.create_member(
        conn,
        {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id, "preferred_time_slot": "Morning"},
    )

    time_slots.set_time_slot_active(conn, slot_id, False)

    assert members.get_member(conn, member_id)["preferred_time_slot"] == "Morning"
