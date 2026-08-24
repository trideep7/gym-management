import datetime

import altair as alt
import pandas as pd
import streamlit as st

import db
from services import reports as reports_service

conn = db.get_connection()

st.title("Reports")

today = datetime.date.today()
start_date = st.date_input("From", value=today - datetime.timedelta(days=6), key="report_start")
end_date = st.date_input("To", value=today, key="report_end")

if st.button("Generate"):
    st.session_state["report_range"] = (start_date, end_date)

report_range = st.session_state.get("report_range")
if report_range is None:
    st.info("Choose a date range and click Generate to view the report.")
else:
    range_start, range_end = report_range

    st.subheader("Sign-Ins")
    counts = reports_service.signin_counts(conn, range_start.isoformat(), range_end.isoformat())
    if counts:
        chart_df = pd.DataFrame(counts)
        bar_size = min(40, max(8, 300 // len(chart_df)))
        chart = (
            alt.Chart(chart_df)
            .mark_bar(size=bar_size)
            .encode(x=alt.X("date:O", title="Date"), y=alt.Y("count:Q", title="Sign-ins"))
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.write("No sign-ins in this date range.")

    st.subheader("Payment Status")
    summary = reports_service.payment_summary(conn)
    col1, col2, col3 = st.columns(3)
    col1.metric("Paid", summary["paid"])
    col2.metric("Overdue", summary["overdue"])
    col3.metric("No Payment Yet", summary["no_payment"])
    if summary["overdue_members"]:
        st.write("Overdue members:")
        for m in summary["overdue_members"]:
            st.write(f"- {m['first_name']} {m['surname'] or ''} ({m['mobile']})")
    if summary["no_payment_members"]:
        st.write("No payment yet:")
        for m in summary["no_payment_members"]:
            st.write(f"- {m['first_name']} {m['surname'] or ''} ({m['mobile']})")
