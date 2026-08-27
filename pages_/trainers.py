import streamlit as st

import db
from services import trainers as trainers_service
from utils import time_slots
from utils.errors import safe_action

conn = db.get_connection()

st.title("Trainers")

if "editing_trainer_id" not in st.session_state:
    st.session_state.editing_trainer_id = None

if st.session_state.get("trainer_flash"):
    st.success(st.session_state.pop("trainer_flash"))

with st.form("new_trainer_form", clear_on_submit=True):
    name = st.text_input("Name", key="trainer_name")
    mobile = st.text_input("Mobile", key="trainer_mobile")
    time_slot = st.selectbox(
        "Time Slot", time_slots.options_for(None), key="trainer_time_slot"
    )
    if st.form_submit_button("Add Trainer", key="add_trainer_button"):
        if name:
            ok, _ = safe_action(
                lambda: trainers_service.create_trainer(
                    conn, name, mobile, time_slots.to_stored(time_slot)
                )
            )
            if ok:
                st.session_state.trainer_flash = f"Added '{name}'."
                st.rerun()
        else:
            st.error("Name is required.")

trainer_list = trainers_service.list_trainers(conn)
if not trainer_list:
    st.write("No trainers added yet.")
else:
    header = st.columns([3, 2, 3, 1, 1])
    header[0].markdown("**Name**")
    header[1].markdown("**Mobile**")
    header[2].markdown("**Time Slot**")
    header[3].markdown("**Edit**")
    header[4].markdown("**Delete**")
    for trainer in trainer_list:
        if st.session_state.editing_trainer_id == trainer["id"]:
            edit_cols = st.columns([3, 2, 3, 1, 1])
            edited_name = edit_cols[0].text_input(
                "Name", value=trainer["name"], key=f"edit_trainer_name_{trainer['id']}", label_visibility="collapsed"
            )
            edited_mobile = edit_cols[1].text_input(
                "Mobile", value=trainer["mobile"] or "", key=f"edit_trainer_mobile_{trainer['id']}", label_visibility="collapsed"
            )
            slot_options = time_slots.options_for(trainer["time_slot"])
            edited_time_slot = edit_cols[2].selectbox(
                "Time Slot", slot_options,
                index=time_slots.index_of(trainer["time_slot"], slot_options),
                key=f"edit_trainer_time_slot_{trainer['id']}", label_visibility="collapsed",
            )
            if edit_cols[3].button("Save", key=f"save_trainer_{trainer['id']}"):
                ok, _ = safe_action(
                    lambda t=trainer: trainers_service.update_trainer(
                        conn, t["id"], edited_name, edited_mobile,
                        time_slots.to_stored(edited_time_slot),
                    )
                )
                if ok:
                    st.session_state.editing_trainer_id = None
                    st.session_state.trainer_flash = "Updated."
                    st.rerun()
            if edit_cols[4].button("Cancel", key=f"cancel_trainer_{trainer['id']}"):
                st.session_state.editing_trainer_id = None
                st.rerun()
        else:
            row = st.columns([3, 2, 3, 1, 1])
            row[0].write(trainer["name"])
            row[1].write(trainer["mobile"] or "—")
            row[2].write(trainer["time_slot"] or "—")
            if row[3].button("Edit", key=f"trainer_edit_{trainer['id']}"):
                st.session_state.editing_trainer_id = trainer["id"]
                st.rerun()
            if row[4].button("Delete", key=f"trainer_delete_{trainer['id']}"):
                ok, result = safe_action(lambda t=trainer: trainers_service.delete_trainer(conn, t["id"]))
                if ok:
                    if result == "deactivated":
                        st.session_state.trainer_flash = (
                            f"'{trainer['name']}' is assigned to a member or has PT payment history, "
                            "so it was deactivated instead of deleted."
                        )
                    else:
                        st.session_state.trainer_flash = f"Trainer '{trainer['name']}' deleted."
                    st.rerun()
