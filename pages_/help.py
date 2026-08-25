import streamlit as st

st.title("Help")
st.caption("Quick how-tos for everyday tasks, plus common issues people run into.")

with st.expander("Signing In Members (Dashboard)"):
    st.markdown(
        """
1. Go to **Dashboard**.
2. Under **Sign In**, search by the member's name or mobile number.
3. Click **Sign In** next to their row.

**Notes:**
- A member can only be signed in **once per day** — signing in again just
  shows the time they already checked in, it won't create a duplicate.
- If the member is **inactive** or has **not paid**, you'll see a
  confirmation popup explaining why before you can sign them in. You can
  still choose "Sign In Anyway" if needed.
- **Today's Sign-Ins** below the search box lists everyone checked in
  today, most recent first.
        """
    )

with st.expander("Members — Add, Edit, View, Search"):
    st.markdown(
        """
**Adding a member**
1. Go to **Members** and click **+ Add Member**.
2. Fill in the form. Fields marked **\\*** are required: **Membership
   Plan**, **Name**, and **Mobile**.
3. Click **Save Member**.

**Editing or viewing a member**
1. Find them in the list (search by name or mobile).
2. Click **View** to see their details, payment history, and reminder
   log.
3. From the View screen, click **Edit** to change their details, or
   **Deactivate Member** if they've left the gym (this doesn't delete
   their record — history is kept).

**Searching**
- The search box matches name **or** mobile number. Use **Show inactive
  members** to include deactivated members in the results.
        """
    )

with st.expander("Payments — Plans, Marking Paid, Reminders"):
    st.markdown(
        """
**Managing plans** (Payments → *Manage Plans* tab)
1. Fill in **Plan Name**, **Amount**, and **Duration (days)**.
2. Click **Add Plan**.
- Deleting a plan removes it only if it's never been used. If any member
  or payment already references it, it's **deactivated** instead (it
  just stops showing up as an option for new members/payments).

**Marking a member as paid** (Payments → *Member Status* tab)
1. Find the member's row (use **Filter by status** to narrow the list).
2. Click **Mark Paid** — this records a payment for their assigned plan
   and pushes their due date forward by the plan's duration.
- **Mark Paid** is disabled if the member has no plan assigned.

**Payment reminders**
- On the *Member Status* tab or a member's View screen, click **Log
  Reminder** (or **Remind Again**) after you've contacted a member about
  an overdue payment, to keep a record of when they were last reminded.
        """
    )

with st.expander("Reminder Message Templates"):
    st.markdown(
        """
Copy-paste templates for contacting members. Fill in `[Name]`, `[Plan]`,
and `[Due Date]` — you'll find these on the Payments page's *Member
Status* tab (the **Due Date** column).

**Upcoming Renewal**
```
Hi [Name], just a reminder that your [Plan] membership at Fitness Tribe
is due for renewal on [Due Date]. Let us know if you'd like to continue
— see you at the gym!
```

**Overdue Payment**
```
Hi [Name], your [Plan] membership at Fitness Tribe expired on [Due Date]
and is now overdue. Please renew at your earliest convenience to keep
your membership active. Let us know if you have any questions!
```

After sending either message, click **Log Reminder** on the Payments
page or the member's View screen so there's a record of it.
        """
    )

with st.expander("Equipment — Inventory"):
    st.markdown(
        """
1. Go to **Equipment**.
2. Fill in **Name** (required), **Quantity**, and optional **Notes**.
3. Click **Add Equipment**.

Use **Delete** next to an item to remove it. This is permanent — there's
no deactivate option for equipment.
        """
    )

with st.expander("Reports"):
    st.markdown(
        """
1. Go to **Reports**.
2. Pick a **From** and **To** date.
3. Click **Generate**.

You'll see a sign-ins chart for that date range, plus a payment status
summary (Paid / Overdue / No Payment Yet) with the members in each
group.
        """
    )

with st.expander("Common Issues"):
    st.markdown(
        """
- **"Mobile number must be exactly 10 digits and cannot start with 0"**
  — mobile numbers must be exactly 10 digits, and the first digit can't
  be 0. For example `9876543210` is valid; `09876543210` (11 digits) and
  `987654321` (9 digits) are not.
- **Can't add a member / no plans in the dropdown** — you need at least
  one **Membership Plan** before you can register a member. Add one
  under Payments → *Manage Plans* first.
- **A mobile number already exists** — the app warns you if a mobile
  number matches an existing active member, but it won't stop you from
  saving anyway. Double-check you're not creating a duplicate record.
- **"Name is required" on Equipment** — the equipment **Name** field
  can't be blank; Quantity and Notes are optional.
- **Report shows nothing / won't generate** — the **From** date must be
  on or before the **To** date.
- **Photo won't upload** — only **JPG** and **PNG** files are accepted
  for member photos.
- **A plan won't delete** — if a plan has ever been used by a member or
  a payment, it can't be hard-deleted; it's deactivated instead so past
  records stay intact.
        """
    )
