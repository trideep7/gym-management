import streamlit as st

import db
from services import payments as payments_service
from utils.errors import safe_action

conn = db.get_connection()

st.title("Membership Plans")

if "editing_plan_id" not in st.session_state:
    st.session_state.editing_plan_id = None

if st.session_state.get("plan_flash"):
    st.success(st.session_state.pop("plan_flash"))

if st.session_state.editing_plan_id is not None:
    plan_id = st.session_state.editing_plan_id
    plan = next(
        (p for p in payments_service.list_plans(conn, active_only=False) if p["id"] == plan_id),
        None,
    )
    if plan is None:  # deleted from another session while this form was open
        st.session_state.editing_plan_id = None
        st.rerun()

    if st.button("← Back to plans", key="plan_edit_cancel"):
        st.session_state.editing_plan_id = None
        st.rerun()

    st.subheader(f"Edit {plan['name']}")
    st.caption(
        "Changes apply to payments recorded from now on. Payments already "
        "taken keep the amount and dates they were recorded with."
    )
    name = st.text_input("Plan Name", value=plan["name"], key="plan_edit_name")
    amount = st.number_input("Amount", min_value=0.0, step=100.0, value=float(plan["amount"]), key="plan_edit_amount")
    duration = st.number_input(
        "Duration (days)", min_value=1, step=1, value=int(plan["duration_days"]), key="plan_edit_duration"
    )
    if st.button("Save Changes", key="plan_edit_save"):
        try:
            payments_service.update_plan(conn, plan_id, name, amount, int(duration))
        except ValueError as e:
            st.error(str(e))
        else:
            st.session_state.editing_plan_id = None
            st.session_state.plan_flash = f"Plan '{name.strip()}' updated."
            st.rerun()

else:
    # Streamlit purges a widget's state while it isn't rendered, and this
    # checkbox disappears whenever the edit form is open -- so the choice
    # is mirrored into a plain session_state key that survives the trip.
    # Without this, editing an inactive plan saves it and then hides it.
    show_inactive = st.checkbox(
        "Show inactive plans",
        value=st.session_state.get("plan_show_inactive_pref", False),
        key="plan_show_inactive",
    )
    st.session_state.plan_show_inactive_pref = show_inactive
    plans_list = payments_service.list_plans(conn, active_only=not show_inactive)
    if not plans_list:
        st.write("No plans added yet.")
    else:
        widths = [3, 2, 2, 1, 1, 2]
        header = st.columns(widths)
        header[0].markdown("**Name**")
        header[1].markdown("**Amount**")
        header[2].markdown("**Duration**")
        header[3].markdown("**Edit**")
        header[4].markdown("**Delete**")
        header[5].markdown("**Status**")
        for plan in plans_list:
            row = st.columns(widths)
            row[0].write(plan["name"])
            row[1].write(f"₹{plan['amount']:.2f}")
            row[2].write(f"{plan['duration_days']} days")
            if row[3].button("Edit", key=f"plan_edit_{plan['id']}"):
                st.session_state.editing_plan_id = plan["id"]
                st.rerun()
            if row[4].button("Delete", key=f"plan_delete_{plan['id']}"):
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
            if plan["is_active"]:
                row[5].write("Active")
            elif row[5].button("Reactivate", key=f"plan_reactivate_{plan['id']}"):
                ok, _ = safe_action(lambda plan=plan: payments_service.set_plan_active(conn, plan["id"], True))
                if ok:
                    st.session_state.plan_flash = f"Plan '{plan['name']}' reactivated."
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
