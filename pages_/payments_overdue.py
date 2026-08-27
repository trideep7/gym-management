import streamlit as st

import db
from pages_ import _payments_common
from services import payments as payments_service
from utils.dates import format_date

conn = db.get_connection()
user = st.session_state.user

st.title("Overdue")
st.caption("Members whose plan has expired and hasn't been renewed.")

entries = payments_service.list_members_with_status(conn, "overdue")

_payments_common.render_payment_table(
    conn,
    user,
    entries,
    date_label="Due Date",
    date_value=lambda entry: format_date(entry["valid_until"]),
    sort_key=lambda entry: entry["valid_until"],
    page_state_key="overdue_page",
    empty_message="Nobody is overdue right now.",
)
