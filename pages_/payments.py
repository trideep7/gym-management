import streamlit as st

import db
from services import payments as payments_service
from services import reminders as reminders_service
from services import trainers as trainers_service
from utils.dates import format_date
from utils.errors import safe_action

conn = db.get_connection()
user = st.session_state.user

st.title("Payments")

tab_status, tab_plans = st.tabs(["Member Status", "Manage Plans"])

with tab_plans:
    st.subheader("Membership Plans")
    if st.session_state.get("plan_flash"):
        st.success(st.session_state.pop("plan_flash"))

    plans_list = payments_service.list_plans(conn)
    if not plans_list:
        st.write("No plans added yet.")
    else:
        header = st.columns([3, 2, 2, 1])
        header[0].markdown("**Name**")
        header[1].markdown("**Amount**")
        header[2].markdown("**Duration**")
        header[3].markdown("**Delete**")
        for plan in plans_list:
            row = st.columns([3, 2, 2, 1])
            row[0].write(plan["name"])
            row[1].write(f"₹{plan['amount']:.2f}")
            row[2].write(f"{plan['duration_days']} days")
            if row[3].button("Delete", key=f"plan_delete_{plan['id']}"):
                ok, result = safe_action(lambda plan=plan: payments_service.delete_plan(conn, plan["id"]))
                if ok:
                    if result == "deactivated":
                        st.session_state.plan_flash = (
                            f"'{plan['name']}' is assigned to a member or has past payments on "
                            "record, so it was deactivated instead of deleted (it won't show up "
                            "for new members or payments anymore)."
                        )
                    else:
                        st.session_state.plan_flash = f"Plan '{plan['name']}' deleted."
                    st.rerun()

    with st.form("new_plan_form", clear_on_submit=True):
        name = st.text_input("Plan Name", key="plan_name")
        amount = st.number_input("Amount", min_value=0.0, step=100.0, key="plan_amount")
        duration = st.number_input("Duration (days)", min_value=1, step=1, value=30, key="plan_duration")
        if st.form_submit_button("Add Plan"):
            payments_service.create_plan(conn, name, amount, int(duration))
            st.session_state.plan_flash = f"Plan '{name}' added."
            st.rerun()

with tab_status:
    if st.session_state.get("payment_flash"):
        st.success(st.session_state.pop("payment_flash"))

    st.subheader("Upcoming Expirations (Next 7 Days)")
    upcoming = payments_service.upcoming_expirations(conn, within_days=7)
    if upcoming:
        upcoming_header = st.columns([2, 2, 2, 2, 2])
        upcoming_header[0].markdown("**Name**")
        upcoming_header[1].markdown("**Phone**")
        upcoming_header[2].markdown("**Plan**")
        upcoming_header[3].markdown("**Expires On**")
        upcoming_header[4].markdown("**Reminder**")
        upcoming_plan_names = {p["id"]: p["name"] for p in payments_service.list_plans(conn, active_only=False)}
        for entry in upcoming:
            upcoming_row = st.columns([2, 2, 2, 2, 2])
            upcoming_row[0].write(f"{entry['first_name']} {entry['surname'] or ''}")
            upcoming_row[1].write(entry["mobile"])
            upcoming_row[2].write(upcoming_plan_names.get(entry.get("plan_id"), "—"))
            upcoming_row[3].write(format_date(entry["valid_until"]))
            last = reminders_service.last_reminder(conn, entry["id"])
            reminder_label = "Log Reminder" if last is None else f"Remind Again — last: {format_date(last['sent_at'][:10])}"
            if upcoming_row[4].button(reminder_label, key=f"expiry_reminder_{entry['id']}"):
                ok, _ = safe_action(lambda entry=entry: reminders_service.log_reminder(conn, entry["id"], user["id"]))
                if ok:
                    st.rerun()
    else:
        st.write("No plans expiring in the next 7 days.")

    status_filter = st.selectbox("Filter by status", ["All", "paid", "overdue", "no_payment"], key="status_filter")
    filter_value = None if status_filter == "All" else status_filter
    entries = payments_service.list_members_with_status(conn, filter_value)
    # include inactive plans here too — a member can still be assigned to a
    # plan that's since been deactivated, and we need its name to display it
    plan_names = {p["id"]: p["name"] for p in payments_service.list_plans(conn, active_only=False)}
    trainer_names = {t["id"]: t["name"] for t in trainers_service.list_trainers(conn, active_only=False)}

    if entries:
        header = st.columns([2, 2, 2, 2, 2, 2, 1, 2])
        header[0].markdown("**Name**")
        header[1].markdown("**Phone**")
        header[2].markdown("**Status**")
        header[3].markdown("**Plan**")
        header[4].markdown("**Last Paid**")
        header[5].markdown("**Due Date**")
        header[6].markdown("**Mark Paid**")
        header[7].markdown("**Reminder**")

    for entry in entries:
        row = st.columns([2, 2, 2, 2, 2, 2, 1, 2])
        row[0].write(f"{entry['first_name']} {entry['surname'] or ''}")
        row[1].write(entry["mobile"])
        row[2].write(entry["status"].replace("_", " ").title())
        member_plan_id = entry.get("plan_id")
        if member_plan_id is not None:
            quoted_amount = payments_service.quote_amount(conn, entry["id"], member_plan_id)
            plan_label = f"{plan_names.get(member_plan_id, '—')} (₹{quoted_amount:.2f})"
            if entry.get("has_pt") and entry.get("trainer_id"):
                plan_label += f" + PT ({trainer_names.get(entry['trainer_id'], '—')})"
            row[3].write(plan_label)
        else:
            row[3].write("No plan assigned")
        last_payment = entry.get("last_payment")
        row[4].write(format_date(last_payment["paid_on"] if last_payment else None))
        row[5].write(format_date(entry["valid_until"]))
        if row[6].button("Mark Paid", key=f"mark_paid_{entry['id']}", disabled=member_plan_id is None):
            ok, result = safe_action(
                lambda: trainers_service.mark_paid_with_pt(conn, entry["id"], member_plan_id, user["id"])
            )
            if ok:
                if result["pt_charged"]:
                    st.session_state.payment_flash = f"Marked {entry['first_name']} as paid (incl. Personal Training)."
                else:
                    st.session_state.payment_flash = f"Marked {entry['first_name']} as paid."
                st.rerun()
        if entry["status"] != "paid":
            last = reminders_service.last_reminder(conn, entry["id"])
            reminder_label = "Log Reminder" if last is None else f"Remind Again — last: {format_date(last['sent_at'][:10])}"
            if row[7].button(reminder_label, key=f"log_reminder_{entry['id']}"):
                ok, _ = safe_action(lambda: reminders_service.log_reminder(conn, entry["id"], user["id"]))
                if ok:
                    st.rerun()
        else:
            row[7].write("—")
