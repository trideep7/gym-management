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


def test_create_member_requires_mobile(conn):
    plan_id = make_plan(conn)
    with pytest.raises(ValueError):
        members.create_member(conn, {"first_name": "Jamie", "plan_id": plan_id})


def test_create_member_requires_plan_id(conn):
    with pytest.raises(ValueError):
        members.create_member(conn, {"first_name": "Jamie", "mobile": "12345"})


def test_create_and_get_member_roundtrip(conn):
    plan_id = make_plan(conn)
    member_id = members.create_member(conn, make_data(conn, plan_id=plan_id))
    fetched = members.get_member(conn, member_id)
    assert fetched["first_name"] == "Jamie"
    assert fetched["mobile"] == "9876543210"
    assert fetched["is_active"] == 1
    assert fetched["plan_id"] == plan_id


def test_update_member_changes_fields(conn):
    member_id = members.create_member(conn, make_data(conn))
    existing = members.get_member(conn, member_id)
    existing["occupation"] = "Engineer"
    members.update_member(conn, member_id, existing)
    assert members.get_member(conn, member_id)["occupation"] == "Engineer"


def test_search_members_matches_name_or_mobile(conn):
    members.create_member(conn, make_data(conn, first_name="Alex", mobile="111"))
    members.create_member(conn, make_data(conn, first_name="Bailey", mobile="222"))
    assert len(members.search_members(conn, "Alex")) == 1
    assert len(members.search_members(conn, "222")) == 1
    assert len(members.search_members(conn, "")) == 2


def test_search_members_excludes_inactive_by_default(conn):
    member_id = members.create_member(conn, make_data(conn))
    members.set_member_active(conn, member_id, False)
    assert members.search_members(conn, "Jamie") == []
    assert len(members.search_members(conn, "Jamie", active_only=False)) == 1


def test_find_by_mobile_returns_matches(conn):
    members.create_member(conn, make_data(conn, mobile="5551234"))
    assert len(members.find_by_mobile(conn, "5551234")) == 1
    assert members.find_by_mobile(conn, "0000000") == []


def test_save_photo_writes_file_and_returns_filename(tmp_path):
    photos_dir = str(tmp_path / "photos")
    filename = members.save_photo(b"fake-image-bytes", member_id=42, ext="jpg", photos_dir=photos_dir)
    assert filename == "member_42.jpg"
    assert os.path.exists(os.path.join(photos_dir, filename))
    with open(os.path.join(photos_dir, filename), "rb") as f:
        assert f.read() == b"fake-image-bytes"
