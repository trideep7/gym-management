import streamlit as st

import db
from services import payments as payments_service
from utils.errors import safe_action

conn = db.get_connection()

st.title("Membership Plans")

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

st.subheader("Add a Plan")
with st.form("new_plan_form", clear_on_submit=True):
    name = st.text_input("Plan Name", key="plan_name")
    amount = st.number_input("Amount", min_value=0.0, step=100.0, key="plan_amount")
    duration = st.number_input("Duration (days)", min_value=1, step=1, value=30, key="plan_duration")
    if st.form_submit_button("Add Plan", key="add_plan_button"):
        if name:
            ok, _ = safe_action(lambda: payments_service.create_plan(conn, name, amount, int(duration)))
            if ok:
                st.session_state.plan_flash = f"Plan '{name}' added."
                st.rerun()
        else:
            st.error("Plan Name is required.")
