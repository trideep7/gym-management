"""Shared rendering for the three payment pages.

Upcoming, Overdue and Never Paid differ only in which members they list
and what the date column means. Keeping the row itself here means Mark
Paid and Log Reminder -- the two actions that actually touch money --
exist in exactly one place.
"""

import datetime

import streamlit as st

import ui
from services import payments as payments_service
from services import reminders as reminders_service
from services import trainers as trainers_service
from utils.dates import format_date
from utils.errors import safe_action

PAGE_SIZE = 20
SORT_EARLIEST = "Earliest first"
SORT_LATEST = "Latest first"
_WIDTHS = [2, 2, 3, 2, 2, 2, 2]


def render_payment_table(
    conn, user, entries, date_label, date_value, sort_key, page_state_key, empty_message
):
    """Render one page of member rows with Mark Paid and Log Reminder.

    `date_value` formats whatever this page's date column means -- when
    the plan expires, when it lapsed, or when they registered.
    `sort_key` returns the same date raw, for ordering.
    """
    if st.session_state.get("payment_flash"):
        st.success(st.session_state.pop("payment_flash"))

    if not entries:
        st.info(empty_message)
        return

    col_search, col_search_btn = st.columns([4, 1], vertical_alignment="bottom")
    query = col_search.text_input("Search by name or mobile", key=f"{page_state_key}_search")
    col_search_btn.button("Search", key=f"{page_state_key}_search_button")

    # a changed query makes whatever page you were on meaningless, same as
    # a changed sort direction below
    last_query_key = f"{page_state_key}_last_search"
    if st.session_state.get(last_query_key) != query:
        st.session_state[last_query_key] = query
        st.session_state[page_state_key] = 1

    if query:
        q = query.strip().lower()
        entries = [
            e for e in entries
            if q in f"{e['first_name']} {e['surname'] or ''}".lower() or q in (e["mobile"] or "").lower()
        ]
        if not entries:
            st.info(f"No members match '{query}'.")
            return

    direction = st.radio(
        f"Sort by {date_label}",
        [SORT_EARLIEST, SORT_LATEST],
        horizontal=True,
        key=f"{page_state_key}_sort",
    )
    # Reversing the list makes whatever page you were on meaningless, so
    # go back to the first one -- same reason the Members list resets when
    # its search query changes.
    last_direction_key = f"{page_state_key}_last_sort"
    if st.session_state.get(last_direction_key) != direction:
        st.session_state[last_direction_key] = direction
        st.session_state[page_state_key] = 1

    entries = sorted(entries, key=sort_key, reverse=direction == SORT_LATEST)

    st.caption(f"{len(entries)} member(s)")
    page_entries, page_controls = ui.paginate(entries, PAGE_SIZE, page_state_key)

    # inactive plans and trainers are included: a member can still be
    # assigned to one that's since been retired, and the row has to name it
    plan_names = {p["id"]: p["name"] for p in payments_service.list_plans(conn, active_only=False)}
    trainer_names = {t["id"]: t["name"] for t in trainers_service.list_trainers(conn, active_only=False)}

    header = st.columns(_WIDTHS)
    header[0].markdown("**Name**")
    header[1].markdown("**Phone**")
    header[2].markdown("**Plan**")
    header[3].markdown("**Last Paid**")
    header[4].markdown(f"**{date_label}**")
    header[5].markdown("**Mark Paid**")
    header[6].markdown("**Reminder**")

    for entry in page_entries:
        row = st.columns(_WIDTHS)
        row[0].write(f"{entry['first_name']} {entry['surname'] or ''}")
        row[1].write(entry["mobile"] or "—")

        plan_id = entry.get("plan_id")
        if plan_id is None:
            row[2].write("No plan assigned")
        else:
            quoted = payments_service.quote_amount(conn, entry["id"], plan_id)
            label = f"{plan_names.get(plan_id, '—')} (₹{quoted:.2f})"
            if entry.get("has_pt") and entry.get("trainer_id"):
                label += f" + PT ({trainer_names.get(entry['trainer_id'], '—')})"
            row[2].write(label)

        last_payment = entry.get("last_payment")
        row[3].write(format_date(last_payment["paid_on"] if last_payment else None))
        row[4].write(date_value(entry))

        marking_key = f"marking_paid_{entry['id']}"
        if st.session_state.get(marking_key):
            row[5].write("Confirm below ↓")
        elif row[5].button("Mark Paid", key=f"mark_paid_{entry['id']}", disabled=plan_id is None):
            st.session_state[marking_key] = True
            st.rerun()

        last_reminder = reminders_service.last_reminder(conn, entry["id"])
        reminder_label = (
            "Log Reminder" if last_reminder is None
            else f"Remind Again — last: {format_date(last_reminder['sent_at'][:10])}"
        )
        if row[6].button(reminder_label, key=f"log_reminder_{entry['id']}"):
            ok, _ = safe_action(
                lambda entry=entry: reminders_service.log_reminder(conn, entry["id"], user["id"])
            )
            if ok:
                st.rerun()

        if st.session_state.get(marking_key):
            mcol1, mcol2, mcol3, mcol4, _mcol_spacer = st.columns(
                [2, 2, 1, 1, 2], vertical_alignment="bottom"
            )
            paid_on = mcol1.date_input(
                "Paid On", value=datetime.date.today(), max_value=datetime.date.today(),
                key=f"paid_on_input_{entry['id']}", format="DD-MM-YYYY",
            )
            method_label = mcol2.radio(
                "Payment Method", ["Offline", "Online"], key=f"payment_method_input_{entry['id']}",
                horizontal=True,
            )
            if mcol3.button("Confirm", key=f"confirm_mark_paid_{entry['id']}"):
                ok, result = safe_action(
                    lambda entry=entry, plan_id=plan_id, paid_on=paid_on, method_label=method_label:
                        trainers_service.mark_paid_with_pt(
                            conn, entry["id"], plan_id, user["id"],
                            paid_on=paid_on, payment_method=method_label.lower(),
                        )
                )
                if ok:
                    suffix = " (incl. Personal Training)" if result["pt_charged"] else ""
                    st.session_state.payment_flash = f"Marked {entry['first_name']} as paid{suffix}."
                    st.session_state.pop(marking_key, None)
                    st.rerun()
            if mcol4.button("Cancel", key=f"cancel_mark_paid_{entry['id']}"):
                st.session_state.pop(marking_key, None)
                st.rerun()

    page_controls()


def render_payment_edit_controls(conn, payment, key_prefix, flash_key, editor_id):
    """Inline edit form / delete-confirmation for one payment row.

    Call right after rendering that payment's own summary row -- an Edit
    button on that row is the caller's responsibility (its column layout
    varies per page), but everything from there on (the amount/date/method
    form, Save, Delete, its confirmation step) lives here once, shared by
    the member view and the Recent Payments page.

    `editor_id` is the logged-in user saving the change, recorded as the
    payment's updated_by so the Recent Payments page can show who touched
    it.

    `key_prefix` namespaces both the widget keys and the session_state
    keys this reads/writes, so two callers on different pages (or two
    tables on the same page) never collide -- session_state is shared
    app-wide, not scoped per page. Pass "" to reproduce unprefixed keys.

    Returns True if this payment is currently showing edit or delete-
    confirmation UI, so the caller can skip anything else for this row.
    """
    editing_key = f"{key_prefix}editing_payment_id"
    confirming_key = f"{key_prefix}confirming_delete_payment_id"

    if st.session_state.get(editing_key) != payment["id"]:
        return False

    if st.session_state.get(confirming_key) == payment["id"]:
        st.warning("Delete this payment permanently? This cannot be undone.")
        conf_col1, conf_col2 = st.columns(2)
        if conf_col1.button("Yes, Delete", key=f"{key_prefix}confirm_delete_payment_{payment['id']}"):
            ok, _ = safe_action(lambda: payments_service.delete_payment(conn, payment["id"]))
            if ok:
                st.session_state[editing_key] = None
                st.session_state[confirming_key] = None
                st.session_state[flash_key] = "Payment deleted."
                st.rerun()
        if conf_col2.button("Cancel", key=f"{key_prefix}cancel_delete_payment_{payment['id']}"):
            st.session_state[confirming_key] = None
            st.rerun()
        return True

    ecol_plan, ecol_amount, ecol1, ecol2, ecol3, ecol4, ecol5, _ecol_spacer = st.columns(
        [2, 1, 2, 2, 1, 1, 1, 1], vertical_alignment="bottom"
    )
    # every plan, including deactivated ones -- a payment already recorded
    # against a retired plan must still show and keep that plan selected
    plan_options = payments_service.list_plans(conn, active_only=False)
    plan_ids = [p["id"] for p in plan_options]
    plan_labels = {p["id"]: p["name"] for p in plan_options}
    current_plan_index = plan_ids.index(payment["plan_id"]) if payment["plan_id"] in plan_ids else 0
    edited_plan_id = ecol_plan.selectbox(
        "Plan", plan_ids, index=current_plan_index,
        format_func=lambda pid: plan_labels.get(pid, "—"),
        key=f"{key_prefix}edit_plan_{payment['id']}",
    )
    edited_amount = ecol_amount.number_input(
        "Amount", min_value=0.0, step=100.0, value=float(payment["amount"]),
        key=f"{key_prefix}edit_amount_{payment['id']}",
    )
    existing_paid_on = datetime.date.fromisoformat(payment["paid_on"])
    # a payment can already be dated past today -- a member paying ahead
    # for a cycle that starts next month is real, valid data, not
    # something the picker should refuse to display
    edited_paid_on = ecol1.date_input(
        "Paid On", value=existing_paid_on,
        max_value=max(datetime.date.today(), existing_paid_on),
        key=f"{key_prefix}edit_paid_on_{payment['id']}",
        format="DD-MM-YYYY",
    )
    default_method_index = 1 if payment["payment_method"] == "online" else 0
    edited_method_label = ecol2.radio(
        "Payment Method", ["Offline", "Online"], index=default_method_index,
        key=f"{key_prefix}edit_payment_method_{payment['id']}", horizontal=True,
    )
    if ecol3.button("Save", key=f"{key_prefix}save_payment_{payment['id']}"):
        ok, _ = safe_action(
            lambda: payments_service.update_payment(
                conn, payment["id"], payment_method=edited_method_label.lower(),
                paid_on=edited_paid_on, amount=edited_amount, plan_id=edited_plan_id,
                updated_by=editor_id,
            )
        )
        if ok:
            st.session_state[editing_key] = None
            st.session_state[flash_key] = "Payment updated."
            st.rerun()
    if ecol4.button("Delete", key=f"{key_prefix}delete_payment_{payment['id']}"):
        st.session_state[confirming_key] = payment["id"]
        st.rerun()
    if ecol5.button("Cancel", key=f"{key_prefix}cancel_edit_payment_{payment['id']}"):
        st.session_state[editing_key] = None
        st.rerun()
    return True


def start_editing_payment(key_prefix, payment_id):
    st.session_state[f"{key_prefix}editing_payment_id"] = payment_id
    st.session_state[f"{key_prefix}confirming_delete_payment_id"] = None
    st.rerun()
