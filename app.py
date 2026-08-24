import streamlit as st

import db
import ui
from services import auth

st.set_page_config(page_title="Fitness Tribe Gym Management", layout="wide")
ui.apply_theme()

conn = db.get_connection()
db.init_db(conn)
db.seed_admin(conn)

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    session_token = st.query_params.get("session")
    if session_token:
        restored_user = auth.get_session_user(conn, session_token)
        if restored_user:
            st.session_state.user = restored_user


def login_view():
    ui.login_logo()
    _, form_col, _ = st.columns([1, 1, 1])
    with form_col:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Log In", key="login_button"):
            user = auth.authenticate(conn, username, password)
            if user:
                st.session_state.user = user
                st.query_params["session"] = auth.create_session(conn, user["id"])
                st.rerun()
            else:
                st.error("Invalid username or password")


if st.session_state.user is None:
    login_view()
else:
    ui.set_sidebar_logo()

    pages = [
        st.Page("pages_/dashboard.py", title="Dashboard", icon="🏠"),
        st.Page("pages_/members.py", title="Members", icon="👥"),
        st.Page("pages_/payments.py", title="Payments", icon="💳"),
        st.Page("pages_/equipment.py", title="Equipment", icon="🏋️"),
        st.Page("pages_/reports.py", title="Reports", icon="📊"),
    ]
    if st.session_state.user["role"] == "admin":
        pages.append(st.Page("pages_/users.py", title="Users", icon="🔑"))

    nav = st.navigation(pages)

    with st.sidebar:
        st.divider()
        st.write(f"**{st.session_state.user['full_name']}** ({st.session_state.user['role']})")
        if st.button("Log Out", key="logout_button"):
            session_token = st.query_params.get("session")
            if session_token:
                auth.delete_session(conn, session_token)
                del st.query_params["session"]
            st.session_state.user = None
            st.rerun()

    nav.run()
