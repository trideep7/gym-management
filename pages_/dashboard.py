import datetime

import streamlit as st

import db
from services import attendance, members, payments
from utils.dates import format_time
from utils.errors import safe_action

conn = db.get_connection()
user = st.session_state.user

st.title("Dashboard")

if st.session_state.get("signin_flash"):
    flash_type, flash_msg = st.session_state.pop("signin_flash")
    if flash_type == "success":
        st.success(flash_msg)
    else:
        st.info(flash_msg)

today = datetime.date.today()
month_start = today.replace(day=1).isoformat()
three_months_ago = (today - datetime.timedelta(days=90)).isoformat()

all_members = members.search_members(conn, "", active_only=True)
today_signins = attendance.list_today(conn)
overdue_count = sum(
    1 for m in all_members if payments.get_status(conn, m["id"])["status"] == "overdue"
)
active_members_count = attendance.active_since_count(conn, three_months_ago)
monthly_active_users = attendance.active_since_count(conn, month_start)
monthly_revenue = payments.revenue_since(conn, month_start)

col1, col2, col3 = st.columns(3)
col1.metric("Total Members", len(all_members))
col2.metric("Active Members", active_members_count)
col3.metric("Monthly Active Users", monthly_active_users)

col4, col5, col6 = st.columns(3)
col4.metric("Checked In Today", len(today_signins))
col5.metric("Payments Overdue", overdue_count)
col6.metric("Monthly Revenue So Far", f"₹{monthly_revenue:.2f}")


def complete_signin(member):
    ok, result = safe_action(lambda: attendance.sign_in(conn, member["id"], user["id"]))
    if ok:
        if result["already_signed_in"]:
            st.session_state.signin_flash = (
                "info",
                f"{member['first_name']} already signed in today at {format_time(result['sign_in_time'])}.",
            )
        else:
            st.session_state.signin_flash = (
                "success",
                f"{member['first_name']} signed in at {format_time(result['sign_in_time'])}.",
            )
        st.session_state.signin_search_key_version += 1
        st.rerun()


@st.dialog("Confirm Sign In")
def confirm_signin_dialog(member, reasons):
    for reason in reasons:
        st.warning(reason)
    display_name = f"{member['first_name']} {member['surname'] or ''}".strip()
    st.write(f"Sign in **{display_name}** anyway?")
    col_confirm, col_cancel = st.columns(2)
    if col_confirm.button("Sign In Anyway", key=f"confirm_signin_{member['id']}"):
        complete_signin(member)
    if col_cancel.button("Cancel", key=f"cancel_signin_{member['id']}"):
        st.rerun()


st.subheader("Sign In")
if "signin_search_key_version" not in st.session_state:
    st.session_state.signin_search_key_version = 0
search_key = f"signin_search_{st.session_state.signin_search_key_version}"

col_search, col_button = st.columns([4, 1], vertical_alignment="bottom")
query = col_search.text_input("Search member by name or mobile", key=search_key)
col_button.button("Search", key="signin_search_button")
results = members.search_members(conn, query) if query else []

for m in results:
    status = payments.get_status(conn, m["id"])
    if status["status"] == "paid":
        badge = "🟢 Paid"
    elif status["status"] == "overdue":
        badge = "🔴 Overdue"
    else:
        badge = "⚪ No payment yet"

    cols = st.columns([3, 2, 2])
    cols[0].write(f"{m['first_name']} {m['surname'] or ''} — {m['mobile']}")
    cols[1].write(badge)
    if cols[2].button("Sign In", key=f"signin_{m['id']}"):
        reasons = []
        if not m["is_active"]:
            reasons.append("This member is marked inactive.")
        if status["status"] != "paid":
            reasons.append(f"This member has not paid (status: {status['status'].replace('_', ' ').title()}).")
        if reasons:
            confirm_signin_dialog(m, reasons)
        else:
            complete_signin(m)

st.subheader("Today's Sign-Ins")
if today_signins:
    SIGNINS_PAGE_SIZE = 10
    if "signins_list_page" not in st.session_state:
        st.session_state.signins_list_page = 1
    total_signin_pages = max(1, -(-len(today_signins) // SIGNINS_PAGE_SIZE))
    st.session_state.signins_list_page = min(max(st.session_state.signins_list_page, 1), total_signin_pages)
    signins_page = st.session_state.signins_list_page
    start = (signins_page - 1) * SIGNINS_PAGE_SIZE
    page_signins = today_signins[start:start + SIGNINS_PAGE_SIZE]

    header = st.columns([3, 2, 2])
    header[0].markdown("**Name**")
    header[1].markdown("**Phone**")
    header[2].markdown("**Time**")
    for row in page_signins:
        row_cols = st.columns([3, 2, 2])
        row_cols[0].write(f"{row['first_name']} {row['surname'] or ''}")
        row_cols[1].write(row["mobile"])
        row_cols[2].write(format_time(row["sign_in_time"]))

    if total_signin_pages > 1:
        col_prev, col_page, col_next = st.columns([1, 2, 1])
        if col_prev.button("← Previous", key="signins_page_prev", disabled=signins_page <= 1):
            st.session_state.signins_list_page -= 1
            st.rerun()
        col_page.write(f"Page {signins_page} of {total_signin_pages}")
        if col_next.button("Next →", key="signins_page_next", disabled=signins_page >= total_signin_pages):
            st.session_state.signins_list_page += 1
            st.rerun()
else:
    st.write("No sign-ins yet today.")
