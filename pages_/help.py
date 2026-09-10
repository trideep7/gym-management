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

**Correcting a past payment**
1. On a member's View screen, find the payment under **Recent Payments**
   and click **Edit**.
2. Fix the **Paid On** date and/or the **Payment Method**, then click
   **Save**. The amount is always recalculated from the plan and the
   member's current locker/PT add-ons — it isn't editable directly.
3. To remove a payment entered by mistake, click **Delete** and confirm.
   This can't be undone.

**Reactivating a member**
1. Check **Show inactive members** in the search filters below — deactivated
   members are hidden from the list by default.
2. Find them, click **View**, then click **Reactivate Member** (the same
   button, now relabeled, on their View screen).

**What being "inactive" affects elsewhere**
- Signing them in on the Dashboard shows a warning popup first, but you
  can still choose to sign them in anyway.
- They're excluded from the Dashboard's **Active Members** count.

**Searching**
- The search box matches name **or** mobile number. Use **Show inactive
  members** to include deactivated members in the results.
        """
    )

with st.expander("Payments — Upcoming, Overdue, Never Paid"):
    st.markdown(
        """
Payments is split into three pages in the sidebar:

- **Upcoming** — members whose plan expires in the next 7 days, soonest
  first. Take renewals here *before* they lapse.
- **Overdue** — members whose plan has already expired.
- **Never Paid** — members who are registered but have no payment on
  record yet.

Each page has a **Sort by** control above the table — *Earliest first*
or *Latest first* on that page's own date column. Each page remembers
its own choice, and switching direction takes you back to page 1.

**Searching**
- Each of the three pages has its own search box above the table,
  matching name **or** mobile number. Clearing it shows everyone again.

**Marking a member as paid**
1. Find the member on whichever of the three pages they're on.
2. Click **Mark Paid** — a small form opens below their row.
3. Set the **Paid On** date (defaults to today) and choose **Offline**
   or **Online**, then click **Confirm** to record the payment.
- **Mark Paid** is disabled if the member has no plan assigned.

**Plan dates don't move when a payment is a day or two off**
A member's plan runs from where their last one ended, not from the day
they happened to pay. Someone on a 15th-of-the-month cycle who pays on
the 13th or the 17th stays on the 15th. Only a member who pays *later*
than the grace window allows (Settings → Gym Settings, 7 days by
default) gets a fresh cycle starting the day they paid.

**Payment reminders**
- Click **Log Reminder** (or **Remind Again**) on any of the three
  pages, or on a member's View screen, after you've contacted someone
  about a payment — it keeps a record of when they were last reminded.
        """
    )

with st.expander("Reminder Message Templates"):
    st.markdown(
        """
Copy-paste templates for contacting members. Fill in `[Name]`, `[Plan]`,
and `[Due Date]` — you'll find these on the **Upcoming** and
**Overdue** pages.

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

After sending either message, click **Log Reminder** on the Upcoming
or Overdue page, or on the member's View screen, so there's a record
of it.
        """
    )

with st.expander("Equipment — Inventory"):
    st.markdown(
        """
1. Go to **Settings → Equipment**.
2. Fill in **Name** (required), **Quantity**, and optional **Notes**.
3. Click **Add Equipment**.

Use **Delete** next to an item to remove it. This is permanent — there's
no deactivate option for equipment.
        """
    )

with st.expander("Settings — Plans, Lockers, Users"):
    st.markdown(
        """
Everything the gym is configured with lives under **Settings** in the
sidebar.

**Membership Plans**
1. Fill in **Plan Name**, **Amount**, and **Duration (days)**.
2. Click **Add Plan**.
- **Edit** corrects a plan's name, price or length. Changes apply to
  payments recorded from then on — payments already taken keep the
  amount and dates they were recorded with, so shortening a plan never
  cuts short cover somebody already paid for.
- Deleting a plan removes it only if it's never been used. If any member
  or payment already references it, it's **deactivated** instead — it
  just stops showing up as an option for new members and payments.
- Tick **Show inactive plans** to see deactivated ones. They can still
  be edited (for the sake of old payment history) and **Reactivate**
  puts one back in use. Editing an inactive plan does not revive it.

**Gym Settings → Total lockers**
Set how many lockers the gym actually has. Once a total is set, ticking
**Has Locker** on a member is refused when they're all taken, and the
member form shows how many are in use. `0` means no limit is being
enforced. Lowering the total below the number already handed out is
refused — free some up first. Nothing is ever taken away automatically.

**Gym Settings → Grace window (days)**
How late a renewal can be and still keep a member's existing plan dates.
At the default of 7, someone due on the 15th who pays on the 13th or the
17th keeps their cycle. Pay later than that and their new plan starts on
the day they paid.

**Users** (admin only)
Create named staff logins rather than sharing the admin account. Users
are deactivated, never deleted, so past payments and sign-ins keep
showing who recorded them.
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
  under Settings → *Membership Plans* first.
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
