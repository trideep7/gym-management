from services import equipment


def test_create_and_list_equipment(conn):
    equipment.create_equipment(conn, "Treadmill", 3, "Near window")
    items = equipment.list_equipment(conn)
    assert len(items) == 1
    assert items[0]["name"] == "Treadmill"
    assert items[0]["quantity"] == 3


def test_update_equipment_changes_fields(conn):
    equipment_id = equipment.create_equipment(conn, "Dumbbell Set", 5)
    equipment.update_equipment(conn, equipment_id, "Dumbbell Set", 8, "Restocked")
    items = equipment.list_equipment(conn)
    assert items[0]["quantity"] == 8
    assert items[0]["notes"] == "Restocked"


def test_delete_equipment_removes_row(conn):
    equipment_id = equipment.create_equipment(conn, "Rowing Machine", 1)
    equipment.delete_equipment(conn, equipment_id)
    assert equipment.list_equipment(conn) == []


def test_list_equipment_orders_by_name(conn):
    equipment.create_equipment(conn, "Zebra Mat", 1)
    equipment.create_equipment(conn, "Ankle Weights", 1)
    names = [item["name"] for item in equipment.list_equipment(conn)]
    assert names == ["Ankle Weights", "Zebra Mat"]
