import streamlit as st

import db
from pages_ import _payments_common
from services import payments as payments_service
from utils.dates import format_date

conn = db.get_connection()
user = st.session_state.user

st.title("Never Paid")
st.caption("Members who are registered but have no payment on record yet.")

entries = payments_service.list_members_with_status(conn, "no_payment")

_payments_common.render_payment_table(
    conn,
    user,
    entries,
    date_label="Registered",
    date_value=lambda entry: format_date(entry["created_at"][:10]),
    sort_key=lambda entry: entry["created_at"],
    page_state_key="never_paid_page",
    empty_message="Every member has at least one payment on record.",
)
