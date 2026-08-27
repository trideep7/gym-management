"""Shared rendering for the three payment pages.

Upcoming, Overdue and Never Paid differ only in which members they list
and what the date column means. Keeping the row itself here means Mark
Paid and Log Reminder -- the two actions that actually touch money --
exist in exactly one place.
"""

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

        if row[5].button("Mark Paid", key=f"mark_paid_{entry['id']}", disabled=plan_id is None):
            ok, result = safe_action(
                lambda entry=entry, plan_id=plan_id: trainers_service.mark_paid_with_pt(
                    conn, entry["id"], plan_id, user["id"]
                )
            )
            if ok:
                suffix = " (incl. Personal Training)" if result["pt_charged"] else ""
                st.session_state.payment_flash = f"Marked {entry['first_name']} as paid{suffix}."
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

    page_controls()
