import datetime

import streamlit as st

import db
import ui
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
# a member can now sign in more than once a day, so this counts distinct
# members rather than total check-in events, to keep meaning "how many
# different people came in today" rather than "how many times the Sign In
# button was clicked today"
checked_in_today_count = len({row["member_id"] for row in today_signins})
overdue_count = sum(
    1 for m in all_members if payments.get_status(conn, m["id"])["status"] == "overdue"
)
active_members_count = attendance.active_since_count(conn, three_months_ago)
monthly_active_users = attendance.active_since_count(conn, month_start)

col1, col2, col3 = st.columns(3)
col1.metric("Total Members", len(all_members))
col2.metric("Active Members", active_members_count)
col3.metric("Monthly Active Users", monthly_active_users)

col4, col5 = st.columns(2)
col4.metric("Checked In Today", checked_in_today_count)
col5.metric("Payments Overdue", overdue_count)


def complete_signin(member):
    ok, result = safe_action(lambda: attendance.sign_in(conn, member["id"], user["id"]))
    if ok:
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


def attempt_signin(member, status):
    reasons = []
    if not member["is_active"]:
        reasons.append("This member is marked inactive.")
    if status["status"] != "paid":
        reasons.append(f"This member has not paid (status: {status['status'].replace('_', ' ').title()}).")
    already_today = attendance.todays_signin_count(conn, member["id"])
    if already_today:
        visit_word = "time" if already_today == 1 else "times"
        reasons.append(f"This member has already signed in {already_today} {visit_word} today.")
    if reasons:
        confirm_signin_dialog(member, reasons)
    else:
        complete_signin(member)


st.subheader("Sign In")
if "signin_search_key_version" not in st.session_state:
    st.session_state.signin_search_key_version = 0
search_key = f"signin_search_{st.session_state.signin_search_key_version}"

col_search, col_button = st.columns([4, 1], vertical_alignment="bottom")
query = col_search.text_input("Search member by name or mobile", key=search_key)
col_button.button("Search", key="signin_search_button")
results = members.search_members(conn, query) if query else []

# an empty result used to render as silence, which reads the same as
# "still searching" -- say which it is
if query:
    if results:
        st.caption(f"{len(results)} member(s) found")
    else:
        st.info(f'No member found matching "{query}". Check the spelling, or try their mobile number.')

for m in results:
    status = payments.get_status(conn, m["id"])
    if status["status"] == "paid":
        badge = "🟢 Paid"
    elif status["status"] == "overdue":
        badge = "🔴 Overdue"
    else:
        badge = "⚪ No payment yet"

    cols = st.columns([3, 2, 2])
    cols[0].write(f"{m['first_name']} {m['surname'] or ''} — {m['mobile'] or 'no phone on file'}")
    cols[1].write(badge)
    with cols[2]:
        if not m["mobile"]:
            phone_value = st.text_input(
                "Mobile", key=f"signin_phone_{m['id']}",
                placeholder="10-digit mobile", label_visibility="collapsed",
            )
            if st.button("Save Phone & Sign In", key=f"signin_save_phone_{m['id']}"):
                if not (phone_value or "").strip():
                    # _validate treats blank as "no phone given" and lets it
                    # through, so this branch has to insist on one itself —
                    # otherwise Save silently re-saves no phone and signs in
                    st.error("Enter a 10-digit mobile number to save and sign in.")
                else:
                    update_data = {col: m.get(col) for col in members.COLUMNS}
                    update_data["mobile"] = phone_value
                    try:
                        members.update_member(conn, m["id"], update_data)
                    except ValueError as e:
                        st.error(str(e))
                    else:
                        attempt_signin({**m, "mobile": phone_value}, status)
        else:
            if st.button("Sign In", key=f"signin_{m['id']}"):
                attempt_signin(m, status)

st.subheader("Today's Sign-Ins")
if today_signins:
    SIGNINS_PAGE_SIZE = 10
    page_signins, signins_page_controls = ui.paginate(
        today_signins, SIGNINS_PAGE_SIZE, "signins_list_page"
    )

    header = st.columns([3, 2, 2])
    header[0].markdown("**Name**")
    header[1].markdown("**Phone**")
    header[2].markdown("**Time**")
    for row in page_signins:
        row_cols = st.columns([3, 2, 2])
        row_cols[0].write(f"{row['first_name']} {row['surname'] or ''}")
        row_cols[1].write(row["mobile"])
        row_cols[2].write(format_time(row["sign_in_time"]))

    signins_page_controls()
else:
    st.write("No sign-ins yet today.")
