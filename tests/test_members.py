import os

import pytest

from services import members, payments


def make_plan(conn):
    return payments.create_plan(conn, "Monthly", 1500.0, 30)


def make_data(conn, **overrides):
    data = {"first_name": "Jamie", "surname": "Lee", "mobile": "9876543210", "plan_id": make_plan(conn)}
    data.update(overrides)
    return data


def test_create_member_requires_first_name(conn):
    plan_id = make_plan(conn)
    with pytest.raises(ValueError):
        members.create_member(conn, {"mobile": "12345", "plan_id": plan_id})


def test_create_member_allows_missing_mobile(conn):
    plan_id = make_plan(conn)
    member_id = members.create_member(conn, {"first_name": "Jamie", "plan_id": plan_id})
    assert members.get_member(conn, member_id)["mobile"] is None


def test_create_member_requires_plan_id(conn):
    with pytest.raises(ValueError):
        members.create_member(conn, {"first_name": "Jamie", "mobile": "12345"})


def test_create_member_rejects_mobile_starting_with_zero(conn):
    plan_id = make_plan(conn)
    with pytest.raises(ValueError):
        members.create_member(conn, {"first_name": "Jamie", "mobile": "0123456789", "plan_id": plan_id})


def test_create_member_rejects_mobile_too_short(conn):
    plan_id = make_plan(conn)
    with pytest.raises(ValueError):
        members.create_member(conn, {"first_name": "Jamie", "mobile": "987654321", "plan_id": plan_id})


def test_create_member_rejects_mobile_too_long(conn):
    plan_id = make_plan(conn)
    with pytest.raises(ValueError):
        members.create_member(conn, {"first_name": "Jamie", "mobile": "98765432109", "plan_id": plan_id})


def test_create_member_rejects_non_digit_mobile(conn):
    plan_id = make_plan(conn)
    with pytest.raises(ValueError):
        members.create_member(conn, {"first_name": "Jamie", "mobile": "98765abcde", "plan_id": plan_id})


def test_create_member_accepts_valid_10_digit_mobile(conn):
    plan_id = make_plan(conn)
    member_id = members.create_member(conn, {"first_name": "Jamie", "mobile": "9876543210", "plan_id": plan_id})
    assert members.get_member(conn, member_id)["mobile"] == "9876543210"


def test_create_and_get_member_roundtrip(conn):
    plan_id = make_plan(conn)
    member_id = members.create_member(conn, make_data(conn, plan_id=plan_id))
    fetched = members.get_member(conn, member_id)
    assert fetched["first_name"] == "Jamie"
    assert fetched["mobile"] == "9876543210"
    assert fetched["is_active"] == 1
    assert fetched["plan_id"] == plan_id


def test_create_member_defaults_locker_and_pt_to_false(conn):
    plan_id = make_plan(conn)
    member_id = members.create_member(conn, make_data(conn, plan_id=plan_id))
    fetched = members.get_member(conn, member_id)
    assert fetched["has_locker"] == 0
    assert fetched["has_pt"] == 0


def test_create_member_persists_locker_and_pt_flags(conn):
    plan_id = make_plan(conn)
    member_id = members.create_member(conn, make_data(conn, plan_id=plan_id, has_locker=True, has_pt=True))
    fetched = members.get_member(conn, member_id)
    assert fetched["has_locker"] == 1
    assert fetched["has_pt"] == 1


def test_update_member_changes_fields(conn):
    member_id = members.create_member(conn, make_data(conn))
    existing = members.get_member(conn, member_id)
    existing["occupation"] = "Engineer"
    members.update_member(conn, member_id, existing)
    assert members.get_member(conn, member_id)["occupation"] == "Engineer"


def test_search_members_matches_name_or_mobile(conn):
    members.create_member(conn, make_data(conn, first_name="Alex", mobile="9111111111"))
    members.create_member(conn, make_data(conn, first_name="Bailey", mobile="9222222222"))
    assert len(members.search_members(conn, "Alex")) == 1
    assert len(members.search_members(conn, "222")) == 1
    assert len(members.search_members(conn, "")) == 2


def test_search_members_excludes_inactive_by_default(conn):
    member_id = members.create_member(conn, make_data(conn))
    members.set_member_active(conn, member_id, False)
    assert members.search_members(conn, "Jamie") == []
    assert len(members.search_members(conn, "Jamie", active_only=False)) == 1


def test_find_by_mobile_returns_matches(conn):
    members.create_member(conn, make_data(conn, mobile="5551234567"))
    assert len(members.find_by_mobile(conn, "5551234567")) == 1
    assert members.find_by_mobile(conn, "9000000000") == []


def test_save_photo_writes_file_and_returns_filename(tmp_path):
    photos_dir = str(tmp_path / "photos")
    filename = members.save_photo(b"fake-image-bytes", member_id=42, ext="jpg", photos_dir=photos_dir)
    assert filename == "member_42.jpg"
    assert os.path.exists(os.path.join(photos_dir, filename))
    with open(os.path.join(photos_dir, filename), "rb") as f:
        assert f.read() == b"fake-image-bytes"


def test_save_photo_rejects_disallowed_extension(tmp_path):
    with pytest.raises(ValueError):
        members.save_photo(b"fake-bytes", member_id=1, ext="exe", photos_dir=str(tmp_path))


def test_save_photo_rejects_path_traversal_disguised_as_extension(tmp_path):
    # Before this fix, an upload whose filename had no "." at all (e.g. one
    # crafted to bypass Streamlit's client-side file_uploader(type=...)
    # filter) would flow straight through as the "extension", and the
    # slashes/".." in it would land in the final filename unescaped.
    with pytest.raises(ValueError):
        members.save_photo(
            b"fake-bytes", member_id=1, ext="../../../tmp/evil", photos_dir=str(tmp_path)
        )
    assert not os.path.exists(os.path.join(str(tmp_path), "..", "..", "..", "tmp", "evil"))


def test_save_photo_accepts_extension_with_leading_dot_and_mixed_case(tmp_path):
    filename = members.save_photo(b"fake-bytes", member_id=7, ext=".PNG", photos_dir=str(tmp_path))
    assert filename == "member_7.png"
    assert os.path.exists(os.path.join(str(tmp_path), "member_7.png"))


def make_trainer(conn, name="Alex"):
    # services/trainers.py doesn't exist until a later task in this plan,
    # so insert directly rather than depending on it here.
    cursor = conn.execute(
        "INSERT INTO trainers (name, mobile, time_slot, is_active, created_at) VALUES (?, ?, ?, 1, ?)",
        (name, "9000000001", "6-8 AM", "2026-01-01T00:00:00"),
    )
    conn.commit()
    return cursor.lastrowid


def test_trainer_id_round_trips_through_create_and_update(conn):
    trainer_id = make_trainer(conn)

    member_id = members.create_member(conn, make_data(conn, trainer_id=trainer_id))
    fetched = members.get_member(conn, member_id)
    assert fetched["trainer_id"] == trainer_id

    members.update_member(conn, member_id, {**fetched, "trainer_id": None})
    updated = members.get_member(conn, member_id)
    assert updated["trainer_id"] is None


def test_trainer_id_defaults_to_null_when_omitted(conn):
    member_id = members.create_member(conn, make_data(conn))
    fetched = members.get_member(conn, member_id)
    assert fetched["trainer_id"] is None


def test_blank_mobile_is_stored_as_null_not_empty_string(conn):
    # "" and NULL must not both mean "no phone" in the DB — find_by_mobile
    # and the dashboard's no-phone branch both key off NULL
    member_id = members.create_member(conn, make_data(conn, mobile=""))
    assert members.get_member(conn, member_id)["mobile"] is None

    existing = members.get_member(conn, member_id)
    members.update_member(conn, member_id, {**existing, "mobile": "   "})
    assert members.get_member(conn, member_id)["mobile"] is None


# --- locker capacity: the gym has a fixed number of lockers

def _fill_lockers(conn, plan_id, count):
    for i in range(count):
        members.create_member(
            conn,
            {"first_name": f"Holder{i}", "mobile": f"90000001{i:02d}",
             "plan_id": plan_id, "has_locker": True},
        )


def test_create_member_with_locker_is_blocked_when_all_lockers_are_taken(conn):
    from services import settings as settings_service

    plan_id = make_plan(conn)
    settings_service.set_locker_count(conn, 2)
    _fill_lockers(conn, plan_id, 2)

    with pytest.raises(ValueError, match="locker"):
        members.create_member(
            conn, {"first_name": "Asha", "mobile": "9000000999", "plan_id": plan_id, "has_locker": True}
        )


def test_create_member_with_locker_succeeds_while_one_is_free(conn):
    from services import settings as settings_service

    plan_id = make_plan(conn)
    settings_service.set_locker_count(conn, 3)
    _fill_lockers(conn, plan_id, 2)

    member_id = members.create_member(
        conn, {"first_name": "Asha", "mobile": "9000000999", "plan_id": plan_id, "has_locker": True}
    )
    assert members.get_member(conn, member_id)["has_locker"] == 1


def test_create_member_without_a_locker_is_unaffected_when_lockers_are_full(conn):
    from services import settings as settings_service

    plan_id = make_plan(conn)
    settings_service.set_locker_count(conn, 1)
    _fill_lockers(conn, plan_id, 1)

    member_id = members.create_member(
        conn, {"first_name": "Asha", "mobile": "9000000999", "plan_id": plan_id}
    )
    assert members.get_member(conn, member_id)["has_locker"] == 0


def test_locker_count_of_zero_means_no_limit_is_enforced(conn):
    # an existing database starts at 0; it must not block every assignment
    plan_id = make_plan(conn)
    _fill_lockers(conn, plan_id, 5)
    member_id = members.create_member(
        conn, {"first_name": "Asha", "mobile": "9000000999", "plan_id": plan_id, "has_locker": True}
    )
    assert members.get_member(conn, member_id)["has_locker"] == 1


def test_editing_a_member_who_already_holds_a_locker_is_not_self_blocked(conn):
    # the Dashboard's quick phone-save calls update_member with the
    # member's existing data -- counting them against their own locker
    # would make a full gym unable to edit its own locker holders
    from services import settings as settings_service

    plan_id = make_plan(conn)
    settings_service.set_locker_count(conn, 2)
    _fill_lockers(conn, plan_id, 2)
    holder = members.search_members(conn, "Holder0")[0]

    members.update_member(conn, holder["id"], {**dict(holder), "mobile": "9111111111"})

    assert members.get_member(conn, holder["id"])["mobile"] == "9111111111"


def test_granting_a_locker_on_edit_is_blocked_when_all_are_taken(conn):
    from services import settings as settings_service

    plan_id = make_plan(conn)
    settings_service.set_locker_count(conn, 2)
    _fill_lockers(conn, plan_id, 2)
    member_id = members.create_member(
        conn, {"first_name": "Asha", "mobile": "9000000999", "plan_id": plan_id}
    )
    existing = dict(members.get_member(conn, member_id))

    with pytest.raises(ValueError, match="locker"):
        members.update_member(conn, member_id, {**existing, "has_locker": True})
