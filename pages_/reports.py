import datetime

import altair as alt
import pandas as pd
import streamlit as st

import db
from services import reports as reports_service
from utils.dates import format_date, preset_range

conn = db.get_connection()
current_user = st.session_state.user

if current_user["role"] != "admin":
    st.error("You do not have access to this page.")
    st.stop()

st.title("Reports")

today = datetime.date.today()

stats = reports_service.overview_stats(conn, today)

col1, col2, col3 = st.columns(3)
col1.metric("Revenue This Month", f"₹{stats['revenue_this_month']:.2f}")
col2.metric("Revenue This Year", f"₹{stats['revenue_this_year']:.2f}")
col3.metric("Active Members", stats["active_members"])

col4, col5 = st.columns(2)
col4.metric("Payments Overdue", stats["payments_overdue"])
col5.metric("Due (Active)", f"₹{stats['due_active']:.2f}")

st.subheader("This Month's Payment Method Breakdown")
method_totals = reports_service.payment_method_breakdown_this_month(conn, today)
col_cash, col_online, col_unspecified = st.columns(3)
col_cash.metric("Cash", f"₹{method_totals['offline']:.2f}")
col_online.metric("Online", f"₹{method_totals['online']:.2f}")
col_unspecified.metric("Unspecified", f"₹{method_totals['unspecified']:.2f}")

st.subheader("Last 12 Months Revenue")
trend = reports_service.monthly_revenue_trend(conn, today)
trend_df = pd.DataFrame(trend)
trend_df["month_label"] = trend_df["month"].apply(
    lambda m: datetime.datetime.strptime(m, "%Y-%m").strftime("%b %Y")
)
# same reasoning as the range charts below: pin the axis to chronological
# order rather than Altair's alphabetical default.
month_order = list(trend_df["month_label"])
bar_size = min(40, max(8, 300 // len(trend_df)))
trend_chart = (
    alt.Chart(trend_df)
    .mark_bar(size=bar_size)
    .encode(x=alt.X("month_label:O", title="Month", sort=month_order), y=alt.Y("total:Q", title="Revenue"))
)
st.altair_chart(trend_chart, use_container_width=True)

st.divider()

PRESETS = ["Today", "Yesterday", "Last 7 Days", "This Month", "Last Month", "This Year", "Custom"]
preset = st.selectbox("Date Range", PRESETS, index=2, key="report_preset")

if preset == "Custom":
    start_date = st.date_input(
        "From", value=today - datetime.timedelta(days=6), key="report_start", format="DD-MM-YYYY"
    )
    end_date = st.date_input("To", value=today, key="report_end", format="DD-MM-YYYY")
else:
    start_date, end_date = preset_range(preset, today)
    st.caption(f"{format_date(start_date)} to {format_date(end_date)}")

if st.button("Generate"):
    if start_date > end_date:
        st.warning("From date must be on or before the To date.")
    else:
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
        chart_df["date"] = chart_df["date"].apply(format_date)
        # counts is already chronologically ordered day-by-day; pin the axis
        # to that row order explicitly, since Altair would otherwise sort
        # these "dd-Mon-yyyy" strings alphabetically (wrong across a month
        # boundary — e.g. "01-Sep-2026" would sort before "28-Aug-2026").
        date_order = list(chart_df["date"])
        bar_size = min(40, max(8, 300 // len(chart_df)))
        chart = (
            alt.Chart(chart_df)
            .mark_bar(size=bar_size)
            .encode(x=alt.X("date:O", title="Date", sort=date_order), y=alt.Y("count:Q", title="Sign-ins"))
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.write("No sign-ins in this date range.")

    st.subheader("Revenue Collected")
    daily_revenue = reports_service.daily_revenue(conn, range_start.isoformat(), range_end.isoformat())
    if daily_revenue:
        revenue_df = pd.DataFrame(daily_revenue)
        revenue_df["date"] = revenue_df["date"].apply(format_date)
        date_order = list(revenue_df["date"])
        bar_size = min(40, max(8, 300 // len(revenue_df)))
        revenue_chart = (
            alt.Chart(revenue_df)
            .mark_bar(size=bar_size)
            .encode(x=alt.X("date:O", title="Date", sort=date_order), y=alt.Y("total:Q", title="Revenue"))
        )
        st.altair_chart(revenue_chart, use_container_width=True)
    else:
        st.write("No payments collected in this date range.")

    st.subheader("Personal Training")
    pt = reports_service.pt_summary(conn, range_start.isoformat(), range_end.isoformat())
    col_pt1, col_pt2, col_pt3 = st.columns(3)
    col_pt1.metric("PT Fees Collected", f"₹{pt['total_fees']:.2f}")
    col_pt2.metric("Owed to Trainers", f"₹{pt['total_trainer_share']:.2f}")
    col_pt3.metric("Gym Share", f"₹{pt['total_gym_share']:.2f}")

    payouts = reports_service.trainer_payouts(conn, range_start.isoformat(), range_end.isoformat())
    if payouts:
        payout_header = st.columns([3, 2])
        payout_header[0].markdown("**Trainer**")
        payout_header[1].markdown("**Amount Owed**")
        for p in payouts:
            payout_row = st.columns([3, 2])
            payout_row[0].write(p["trainer_name"] or "⚠️ Not assigned to a trainer")
            payout_row[1].write(f"₹{p['amount_owed']:.2f}")
        if any(p["trainer_id"] is None for p in payouts):
            st.caption(
                "Some members are paying the Personal Training fee without a "
                "trainer assigned. Assign one on their member page (Members → "
                "View → Edit) so this amount is credited to the right trainer."
            )
    else:
        st.write("No trainers added yet.")
