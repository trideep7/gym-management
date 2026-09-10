import datetime

import streamlit as st

import db
import ui
from pages_ import _payments_common
from services import payments as payments_service
from utils.dates import format_date, preset_range

conn = db.get_connection()
user = st.session_state.user

st.title("Recent")
st.caption("Payments added or edited recently.")

if st.session_state.get("payment_flash"):
    st.success(st.session_state.pop("payment_flash"))

PRESETS = ["Today", "Yesterday", "Last 7 Days", "Last 30 Days", "Last 90 Days", "This Month", "This Year"]
preset = st.selectbox("Date Range", PRESETS, index=2, key="recent_payments_preset")
today = datetime.date.today()
start_date, end_date = preset_range(preset, today)
st.caption(f"{format_date(start_date)} to {format_date(end_date)}")

col_search, col_search_btn = st.columns([4, 1], vertical_alignment="bottom")
query = col_search.text_input("Search by name or mobile", key="recent_payments_search")
col_search_btn.button("Search", key="recent_payments_search_button")

# a changed query or date range makes whatever page you were on meaningless
last_filter_key = "recent_payments_last_filter"
current_filter = (preset, query)
if st.session_state.get(last_filter_key) != current_filter:
    st.session_state[last_filter_key] = current_filter
    st.session_state["recent_payments_page"] = 1

raw_entries = payments_service.recent_payments(conn, start_date.isoformat(), end_date.isoformat())

if not raw_entries:
    st.info("No payment activity in this date range.")
else:
    if query:
        q = query.strip().lower()
        entries = [
            e for e in raw_entries
            if q in f"{e['member_first_name']} {e['member_surname'] or ''}".lower()
            or q in (e["member_mobile"] or "").lower()
        ]
    else:
        entries = raw_entries

    if not entries:
        st.info(f"No members match '{query}'.")
    else:
        st.caption(f"{len(entries)} payment(s)")
        PAGE_SIZE = 20
        page_entries, page_controls = ui.paginate(entries, PAGE_SIZE, "recent_payments_page")

        widths = [3, 2, 2, 2, 2, 2, 2, 2]
        header = st.columns(widths)
        header[0].markdown("**Name**")
        header[1].markdown("**Phone**")
        header[2].markdown("**Plan**")
        header[3].markdown("**Amount**")
        header[4].markdown("**Paid On**")
        header[5].markdown("**Method**")
        header[6].markdown("**Activity**")
        header[7].markdown("**Edit**")
        for entry in page_entries:
            row = st.columns(widths)
            row[0].write(f"{entry['member_first_name']} {entry['member_surname'] or ''}")
            row[1].write(entry["member_mobile"] or "—")
            row[2].write(entry["plan_name"])
            row[3].write(f"₹{entry['amount']:.2f}")
            row[4].write(format_date(entry["paid_on"]))
            row[5].write((entry["payment_method"] or "—").title())
            action = "Added" if entry["created_at"] == entry["updated_at"] else "Edited"
            if entry["updated_by_name"]:
                who = f"{(entry['updated_by_role'] or '').title()} ({entry['updated_by_name']})"
            else:
                who = "System"
            row[6].write(f"{action} {format_date(entry['updated_at'][:10])} by {who}")
            if row[7].button("Edit", key=f"recent_edit_payment_{entry['id']}"):
                _payments_common.start_editing_payment("recent_", entry["id"])
            _payments_common.render_payment_edit_controls(conn, entry, "recent_", "payment_flash", user["id"])

        page_controls()
