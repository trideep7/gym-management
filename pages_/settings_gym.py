import streamlit as st

import db
from services import settings as settings_service
from utils.errors import safe_action

conn = db.get_connection()

st.title("Gym Settings")

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
