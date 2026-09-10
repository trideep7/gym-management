import streamlit as st

import db
from services import auth as auth_service
from utils.errors import report_unexpected_error, safe_action

conn = db.get_connection()
current_user = st.session_state.user

if current_user["role"] != "admin":
    st.error("You do not have access to this page.")
    st.stop()

st.title("Users")

if st.session_state.get("user_flash"):
    st.success(st.session_state.pop("user_flash"))

st.subheader("Existing Users")
for u in auth_service.list_users(conn):
    cols = st.columns([3, 2, 2, 2])
    cols[0].write(f"{u['full_name']} ({u['username']})")
    cols[1].write(u["role"])
    cols[2].write("Active" if u["is_active"] else "Inactive")
    toggle_label = "Deactivate" if u["is_active"] else "Reactivate"
    if cols[3].button(toggle_label, key=f"user_toggle_{u['id']}"):
        ok, _ = safe_action(lambda u=u: auth_service.set_user_active(conn, u["id"], not u["is_active"]))
        if ok:
            st.rerun()

with st.expander("Add Staff User"):
    with st.form("new_user_form", clear_on_submit=True):
        username = st.text_input("Username", key="new_user_username")
        full_name = st.text_input("Full Name", key="new_user_full_name")
        password = st.text_input("Password", type="password", key="new_user_password")
        role = st.selectbox("Role", ["staff", "admin"], key="new_user_role")
        if st.form_submit_button("Create User"):
            try:
                auth_service.create_user(conn, username, password, full_name, role)
                st.session_state.user_flash = f"User '{username}' created."
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except Exception:
                report_unexpected_error()

with st.expander("Reset a Password"):
    users = auth_service.list_users(conn)
    user_options = {u["id"]: u["username"] for u in users}
    with st.form("reset_password_form", clear_on_submit=True):
        target_id = st.selectbox(
            "User", list(user_options.keys()), format_func=lambda uid: user_options[uid], key="reset_target"
        )
        new_password = st.text_input("New Password", type="password", key="reset_new_password")
        if st.form_submit_button("Reset Password"):
            ok, _ = safe_action(lambda: auth_service.reset_password(conn, target_id, new_password))
            if ok:
                st.session_state.user_flash = "Password reset."
                st.rerun()
