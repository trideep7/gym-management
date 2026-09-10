import streamlit as st

import db
from services import equipment as equipment_service
from utils.errors import safe_action

conn = db.get_connection()
current_user = st.session_state.user

if current_user["role"] != "admin":
    st.error("You do not have access to this page.")
    st.stop()

st.title("Equipment")

if st.session_state.get("equipment_flash"):
    st.success(st.session_state.pop("equipment_flash"))

st.subheader("Inventory")
items = equipment_service.list_equipment(conn)
if not items:
    st.write("No equipment added yet.")
else:
    header = st.columns([3, 1, 4, 1])
    header[0].markdown("**Name**")
    header[1].markdown("**Qty**")
    header[2].markdown("**Notes**")
    header[3].markdown("**Delete**")
    for item in items:
        row = st.columns([3, 1, 4, 1])
        row[0].write(item["name"])
        row[1].write(item["quantity"])
        row[2].write(item["notes"] or "—")
        if row[3].button("Delete", key=f"equip_delete_{item['id']}"):
            ok, _ = safe_action(lambda item=item: equipment_service.delete_equipment(conn, item["id"]))
            if ok:
                st.rerun()

with st.expander("Add Equipment"):
    with st.form("new_equipment_form", clear_on_submit=True):
        name = st.text_input("Name", key="equip_name")
        quantity = st.number_input("Quantity", min_value=0, step=1, key="equip_quantity")
        notes = st.text_area("Notes", key="equip_notes")
        if st.form_submit_button("Add Equipment"):
            if name:
                ok, _ = safe_action(lambda: equipment_service.create_equipment(conn, name, int(quantity), notes))
                if ok:
                    st.session_state.equipment_flash = f"Added '{name}'."
                    st.rerun()
            else:
                st.error("Name is required.")
