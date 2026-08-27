import streamlit as st

import db
from pages_ import _payments_common
from services import payments as payments_service
from utils.dates import format_date

WITHIN_DAYS = 7

conn = db.get_connection()
user = st.session_state.user

st.title("Upcoming")
st.caption(f"Members whose plan expires in the next {WITHIN_DAYS} days, soonest first.")

_payments_common.render_payment_table(
    conn,
    user,
    payments_service.upcoming_expirations(conn, within_days=WITHIN_DAYS),
    date_label="Expires On",
    date_value=lambda entry: format_date(entry["valid_until"]),
    sort_key=lambda entry: entry["valid_until"],
    page_state_key="upcoming_page",
    empty_message=f"No plans expiring in the next {WITHIN_DAYS} days.",
)
