import streamlit as st

import db
from services import settings as settings_service
from services import time_slots as time_slots_service
from utils.errors import safe_action

conn = db.get_connection()
current_user = st.session_state.user

if current_user["role"] != "admin":
    st.error("You do not have access to this page.")
    st.stop()

st.title("Gym Settings")

if "editing_time_slot_id" not in st.session_state:
    st.session_state.editing_time_slot_id = None

if st.session_state.get("settings_flash"):
    st.success(st.session_state.pop("settings_flash"))

total_lockers = settings_service.get_locker_count(conn)
in_use = settings_service.lockers_in_use(conn)

st.subheader("Lockers")
if total_lockers > 0:
    st.caption(f"{in_use} of {total_lockers} lockers in use.")
else:
    st.caption(
        f"{in_use} locker(s) assigned. No total is set yet, so nothing is being "
        "enforced — enter one below to start."
    )
locker_count = st.number_input(
    "Total lockers", min_value=0, step=1, value=total_lockers, key="settings_locker_count",
    help="0 means no limit. Once set, a member can't be given a locker beyond this total.",
)

st.subheader("Renewals")
grace_days = st.number_input(
    "Grace window (days)", min_value=0, step=1,
    value=settings_service.get_renewal_grace_days(conn), key="settings_grace_days",
    help=(
        "How late a renewal can be and still keep the member's existing plan dates. "
        "Pay within this window and the cycle is untouched; later than it, the new "
        "plan starts on the day they paid."
    ),
)

if st.button("Save", key="settings_gym_save"):
    # lowering the total below what's already handed out would leave the
    # gym in a state it can't represent; nothing is ever auto-revoked
    if 0 < int(locker_count) < in_use:
        st.error(
            f"{in_use} lockers are currently in use, so the total can't be set to "
            f"{int(locker_count)}. Free some up first, or enter {in_use} or more."
        )
    else:
        def _save():
            settings_service.set_locker_count(conn, int(locker_count))
            settings_service.set_renewal_grace_days(conn, int(grace_days))

        ok, _ = safe_action(_save)
        if ok:
            st.session_state.settings_flash = "Settings saved."
            st.rerun()

st.subheader("Timing Options")
st.caption("The timing choices offered on the member and trainer forms.")

# mirrors show_inactive on the Membership Plans page: the checkbox itself
# is purged from state whenever an edit row replaces it, so the choice is
# mirrored into a plain key that survives the trip
show_inactive_slots = st.checkbox(
    "Show inactive timing options",
    value=st.session_state.get("time_slot_show_inactive_pref", False),
    key="time_slot_show_inactive",
)
st.session_state.time_slot_show_inactive_pref = show_inactive_slots
slot_list = time_slots_service.list_time_slots(conn, active_only=not show_inactive_slots)

if not slot_list:
    st.write("No timing options added yet.")
else:
    slot_widths = [4, 1, 1, 2]
    slot_header = st.columns(slot_widths)
    slot_header[0].markdown("**Label**")
    slot_header[1].markdown("**Edit**")
    slot_header[2].markdown("**Delete**")
    slot_header[3].markdown("**Status**")
    for slot in slot_list:
        if st.session_state.editing_time_slot_id == slot["id"]:
            edit_cols = st.columns(slot_widths)
            edited_label = edit_cols[0].text_input(
                "Label", value=slot["label"], key=f"edit_time_slot_label_{slot['id']}",
                label_visibility="collapsed",
            )
            if edit_cols[1].button("Save", key=f"save_time_slot_{slot['id']}"):
                ok, _ = safe_action(
                    lambda s=slot, edited_label=edited_label:
                        time_slots_service.update_time_slot(conn, s["id"], edited_label)
                )
                if ok:
                    st.session_state.editing_time_slot_id = None
                    st.session_state.settings_flash = "Timing option updated."
                    st.rerun()
            if edit_cols[2].button("Cancel", key=f"cancel_time_slot_{slot['id']}"):
                st.session_state.editing_time_slot_id = None
                st.rerun()
        else:
            slot_row = st.columns(slot_widths)
            slot_row[0].write(slot["label"])
            if slot_row[1].button("Edit", key=f"time_slot_edit_{slot['id']}"):
                st.session_state.editing_time_slot_id = slot["id"]
                st.rerun()
            if slot_row[2].button("Delete", key=f"time_slot_delete_{slot['id']}"):
                ok, result = safe_action(lambda s=slot: time_slots_service.delete_time_slot(conn, s["id"]))
                if ok:
                    if result == "deactivated":
                        st.session_state.settings_flash = (
                            f"'{slot['label']}' is in use by a member or trainer, so it was "
                            "deactivated instead of deleted."
                        )
                    else:
                        st.session_state.settings_flash = f"Timing option '{slot['label']}' deleted."
                    st.rerun()
            if slot["is_active"]:
                slot_row[3].write("Active")
            elif slot_row[3].button("Reactivate", key=f"time_slot_reactivate_{slot['id']}"):
                ok, _ = safe_action(lambda s=slot: time_slots_service.set_time_slot_active(conn, s["id"], True))
                if ok:
                    st.session_state.settings_flash = f"'{slot['label']}' reactivated."
                    st.rerun()

with st.expander("Add Timing Option"):
    with st.form("new_time_slot_form", clear_on_submit=True):
        new_slot_label = st.text_input("Label", key="new_time_slot_label")
        if st.form_submit_button("Add Timing Option"):
            if new_slot_label:
                ok, _ = safe_action(lambda: time_slots_service.create_time_slot(conn, new_slot_label))
                if ok:
                    st.session_state.settings_flash = f"'{new_slot_label}' added."
                    st.rerun()
            else:
                st.error("Label is required.")
