from services import members, payments, trainers


def test_create_and_list_trainers(conn):
    trainer_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    listed = trainers.list_trainers(conn)
    assert len(listed) == 1
    assert listed[0]["id"] == trainer_id
    assert listed[0]["name"] == "Alex"
    assert listed[0]["mobile"] == "9000000001"
    assert listed[0]["time_slot"] == "6-8 AM"
    assert listed[0]["is_active"] == 1


def test_list_trainers_orders_by_name(conn):
    trainers.create_trainer(conn, "Priya", "9000000002", "4-6 PM")
    trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    names = [t["name"] for t in trainers.list_trainers(conn)]
    assert names == ["Alex", "Priya"]


def test_update_trainer_changes_fields(conn):
    trainer_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    trainers.update_trainer(conn, trainer_id, "Alexander", "9000000009", "8-10 AM")
    updated = trainers.list_trainers(conn)[0]
    assert updated["name"] == "Alexander"
    assert updated["mobile"] == "9000000009"
    assert updated["time_slot"] == "8-10 AM"


def test_set_trainer_active_hides_from_default_list(conn):
    trainer_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    trainers.set_trainer_active(conn, trainer_id, False)
    active_names = {t["name"] for t in trainers.list_trainers(conn)}
    assert "Alex" not in active_names
    all_names = {t["name"] for t in trainers.list_trainers(conn, active_only=False)}
    assert "Alex" in all_names


def test_delete_trainer_removes_unused_trainer_completely(conn):
    trainer_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    result = trainers.delete_trainer(conn, trainer_id)
    assert result == "deleted"
    all_names = {t["name"] for t in trainers.list_trainers(conn, active_only=False)}
    assert "Alex" not in all_names


def test_delete_trainer_deactivates_trainer_assigned_to_a_member(conn):
    trainer_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id, "trainer_id": trainer_id})

    result = trainers.delete_trainer(conn, trainer_id)

    assert result == "deactivated"
    all_trainers = {t["id"]: t for t in trainers.list_trainers(conn, active_only=False)}
    assert trainer_id in all_trainers
    assert all_trainers[trainer_id]["is_active"] == 0


def test_delete_trainer_deactivates_trainer_with_payment_history(conn):
    trainer_id = trainers.create_trainer(conn, "Alex", "9000000001", "6-8 AM")
    plan_id = payments.create_plan(conn, "Monthly", 1000.0, 30)
    member_id = members.create_member(conn, {"first_name": "Sam", "mobile": "9000000111", "plan_id": plan_id})
    from services import auth
    user_id = auth.create_user(conn, "staffer", "pw12345", "Staff One", "staff")
    trainers.record_trainer_payment(conn, member_id, trainer_id, 3000, 2000, user_id)

    result = trainers.delete_trainer(conn, trainer_id)

    assert result == "deactivated"
