import logging

import streamlit as st

import db
import logging_setup
import ui
from services import auth
from utils.errors import safe_action

logging_setup.setup_logging()
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Fitness Tribe Gym Management", layout="wide")
ui.apply_theme()

try:
    conn = db.get_connection()
    db.init_db(conn)
    db.seed_admin(conn)
except Exception:
    logger.exception("Failed to start the app (database initialization)")
    st.error(
        "Couldn't start the app — there may be a problem with the data "
        "folder permissions. Please check that the app has write access to "
        "its data folder and restart."
    )
    st.stop()

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    session_token = st.query_params.get("session")
    if session_token:
        try:
            restored_user = auth.get_session_user(conn, session_token)
        except Exception:
            # Failing open to the login screen is the right degraded
            # behavior here — logging it is enough; showing an alarming
            # error banner on top of "please log in again" would be worse,
            # not better.
            logger.exception("Failed to restore session from token")
            restored_user = None
        if restored_user:
            st.session_state.user = restored_user


def login_view():
    ui.login_logo()
    _, form_col, _ = st.columns([1, 1, 1])
    with form_col:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Log In", key="login_button"):
            def _do_login():
                user = auth.authenticate(conn, username, password)
                if user is None:
                    return None
                token = auth.create_session(conn, user["id"])
                return user, token

            ok, result = safe_action(_do_login)
            if ok:
                if result is None:
                    st.error("Invalid username or password")
                else:
                    user, token = result
                    st.session_state.user = user
                    st.query_params["session"] = token
                    st.rerun()


if st.session_state.user is None:
    # st.navigation must be called on every rerun, even here — Streamlit
    # keeps showing whatever page set the *last* st.navigation() call
    # registered until a new call overrides it, so without this the sidebar
    # nav from before logout stayed visible next to the login form.
    login_page = st.navigation([st.Page(login_view, title="Login")], position="hidden")
    login_page.run()
else:
    ui.set_sidebar_logo()

    # a dict groups the sidebar under headings; the "" key holds the
    # entries that stay at the top level, above any heading
    pages = {
        "": [
            st.Page("pages_/dashboard.py", title="Dashboard", icon="🏠"),
            st.Page("pages_/members.py", title="Members", icon="👥"),
            st.Page("pages_/trainers.py", title="Trainers", icon="🧑‍🏫"),
            st.Page("pages_/reports.py", title="Reports", icon="📊"),
            st.Page("pages_/help.py", title="Help", icon="❓"),
        ],
        "Payments": [
            st.Page("pages_/payments_upcoming.py", title="Upcoming", icon="⏳"),
            st.Page("pages_/payments_overdue.py", title="Overdue", icon="🔴"),
            st.Page("pages_/payments_never_paid.py", title="Never Paid", icon="⚪"),
        ],
        "Settings": [
            st.Page("pages_/settings_plans.py", title="Membership Plans", icon="💳"),
            st.Page("pages_/settings_gym.py", title="Gym Settings", icon="⚙️"),
            st.Page("pages_/equipment.py", title="Equipment", icon="🏋️"),
        ],
    }
    if st.session_state.user["role"] == "admin":
        pages["Settings"].append(st.Page("pages_/users.py", title="Users", icon="🔑"))

    nav = st.navigation(pages)

    with st.sidebar:
        st.divider()
        st.write(f"**{st.session_state.user['full_name']}** ({st.session_state.user['role']})")
        if st.button("Log Out", key="logout_button"):
            session_token = st.query_params.get("session")
            if session_token:
                safe_action(lambda: auth.delete_session(conn, session_token))
                del st.query_params["session"]
            st.session_state.user = None
            st.rerun()

    nav.run()
