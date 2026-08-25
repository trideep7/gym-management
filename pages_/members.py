import datetime

import streamlit as st

import db
from services import members as members_service
from services import payments as payments_service
from utils.errors import report_unexpected_error, safe_action

conn = db.get_connection()

st.title("Members")

TIME_SLOTS = [
    "6:00 AM - 8:00 AM",
    "8:00 AM - 10:00 AM",
    "10:00 AM - 4:00 PM",
    "4:00 PM - 6:00 PM",
]
GENDERS = ["Female", "Male", "Other"]


def member_form(key_prefix, existing=None):
    existing = existing or {}

    plans = payments_service.list_plans(conn)
    if not plans:
        st.warning("Add a membership plan first (Payments → Manage Plans) before registering a member.")
        return None, None

    data = {"photo_path": existing.get("photo_path")}

    st.caption("Fields marked with * are required.")

    plan_ids = [p["id"] for p in plans]
    plan_labels = {p["id"]: p["name"] for p in plans}
    current_plan_id = existing.get("plan_id")
    plan_index = plan_ids.index(current_plan_id) if current_plan_id in plan_ids else 0
    data["plan_id"] = st.selectbox(
        "Membership Plan *", plan_ids, index=plan_index,
        format_func=lambda pid: plan_labels[pid], key=f"{key_prefix}_plan_id",
    )

    col1, col2 = st.columns(2)
    data["surname"] = col1.text_input("Surname", value=existing.get("surname", ""), key=f"{key_prefix}_surname")
    data["first_name"] = col2.text_input("Name *", value=existing.get("first_name", ""), key=f"{key_prefix}_first_name")
    data["address"] = st.text_input("Address", value=existing.get("address", ""), key=f"{key_prefix}_address")

    col3, col4, col5 = st.columns(3)
    data["mobile"] = col3.text_input("Mobile *", value=existing.get("mobile", ""), key=f"{key_prefix}_mobile")
    data["email"] = col4.text_input("Email", value=existing.get("email", ""), key=f"{key_prefix}_email")
    data["instagram_id"] = col5.text_input("Instagram ID", value=existing.get("instagram_id", ""), key=f"{key_prefix}_instagram")

    data["occupation"] = st.text_input("Occupation", value=existing.get("occupation", ""), key=f"{key_prefix}_occupation")
    data["is_student"] = st.checkbox("Student", value=bool(existing.get("is_student", 0)), key=f"{key_prefix}_is_student")

    col6, col7 = st.columns(2)
    data["school_college_name"] = col6.text_input(
        "School/College Name", value=existing.get("school_college_name", ""), key=f"{key_prefix}_school"
    )
    data["grade_semester"] = col7.text_input(
        "Grade/Semester", value=existing.get("grade_semester", ""), key=f"{key_prefix}_grade"
    )

    col8, col9 = st.columns(2)
    dob_value = existing.get("dob")
    data["dob"] = col8.date_input(
        "Date of Birth",
        value=datetime.date.fromisoformat(dob_value) if dob_value else None,
        min_value=datetime.date(1920, 1, 1),
        key=f"{key_prefix}_dob",
    )
    gender_index = GENDERS.index(existing["gender"]) if existing.get("gender") in GENDERS else 0
    data["gender"] = col9.selectbox("Gender", GENDERS, index=gender_index, key=f"{key_prefix}_gender")

    data["how_found_us"] = st.text_area(
        "How do you find our Gym, any feedback?", value=existing.get("how_found_us", ""), key=f"{key_prefix}_how_found"
    )
    slot_index = TIME_SLOTS.index(existing["preferred_time_slot"]) if existing.get("preferred_time_slot") in TIME_SLOTS else 0
    data["preferred_time_slot"] = st.selectbox("Preferred Timing", TIME_SLOTS, index=slot_index, key=f"{key_prefix}_time_slot")

    st.subheader("Medical Questionnaire")
    st.write("Have you ever or do you have any of the following?")
    mc1, mc2, mc3, mc4 = st.columns(4)
    data["med_heart_disease"] = mc1.checkbox("Heart Disease", value=bool(existing.get("med_heart_disease", 0)), key=f"{key_prefix}_med_heart")
    data["med_dizziness"] = mc2.checkbox("Dizziness", value=bool(existing.get("med_dizziness", 0)), key=f"{key_prefix}_med_dizzy")
    data["med_blackouts"] = mc3.checkbox("Blackouts", value=bool(existing.get("med_blackouts", 0)), key=f"{key_prefix}_med_blackouts")
    data["med_asthma"] = mc4.checkbox("Asthma", value=bool(existing.get("med_asthma", 0)), key=f"{key_prefix}_med_asthma")

    mc5, mc6, mc7 = st.columns(3)
    data["med_high_low_bp"] = mc5.checkbox("High/Low Blood Pressure", value=bool(existing.get("med_high_low_bp", 0)), key=f"{key_prefix}_med_bp")
    data["med_diabetes"] = mc6.checkbox("Diabetes", value=bool(existing.get("med_diabetes", 0)), key=f"{key_prefix}_med_diabetes")
    data["med_gout"] = mc7.checkbox("Gout", value=bool(existing.get("med_gout", 0)), key=f"{key_prefix}_med_gout")
    data["med_other_condition"] = st.text_input(
        "Other condition", value=existing.get("med_other_condition", ""), key=f"{key_prefix}_med_other"
    )

    st.write("Do you have any problems/injuries in the following areas?")
    ic1, ic2, ic3, ic4 = st.columns(4)
    data["injury_knees"] = ic1.checkbox("Knees", value=bool(existing.get("injury_knees", 0)), key=f"{key_prefix}_injury_knees")
    data["injury_lower_back"] = ic2.checkbox("Lower Back", value=bool(existing.get("injury_lower_back", 0)), key=f"{key_prefix}_injury_back")
    data["injury_neck_shoulder"] = ic3.checkbox("Neck/Shoulder", value=bool(existing.get("injury_neck_shoulder", 0)), key=f"{key_prefix}_injury_neck")
    data["injury_hips_pelvic"] = ic4.checkbox("Hips/Pelvic", value=bool(existing.get("injury_hips_pelvic", 0)), key=f"{key_prefix}_injury_hips")
    data["injury_other"] = st.text_input(
        "Other injury area", value=existing.get("injury_other", ""), key=f"{key_prefix}_injury_other"
    )

    data["surgery_details"] = st.text_area(
        "Surgery in the last 5 years? If yes, when & what?", value=existing.get("surgery_details", ""), key=f"{key_prefix}_surgery"
    )
    data["medication_details"] = st.text_area(
        "On any medication? If yes, what and when?", value=existing.get("medication_details", ""), key=f"{key_prefix}_medication"
    )
    data["additional_notes"] = st.text_area(
        "Anything else we need to know?", value=existing.get("additional_notes", ""), key=f"{key_prefix}_notes"
    )

    photo_file = st.file_uploader("Photo", type=["jpg", "jpeg", "png"], key=f"{key_prefix}_photo")

    if data["dob"] is not None:
        data["dob"] = data["dob"].isoformat()

    return data, photo_file


def save_uploaded_photo(member_id, photo_file, data):
    if photo_file is None:
        return
    ext = photo_file.name.split(".")[-1]
    filename = members_service.save_photo(photo_file.getvalue(), member_id, ext, db.get_photos_dir())
    members_service.update_member(conn, member_id, {**data, "photo_path": filename})


FORM_FIELD_SUFFIXES = [
    "plan_id", "surname", "first_name", "address", "mobile", "email", "instagram",
    "occupation", "is_student", "school", "grade", "dob", "gender",
    "how_found", "time_slot", "med_heart", "med_dizzy", "med_blackouts",
    "med_asthma", "med_bp", "med_diabetes", "med_gout", "med_other",
    "injury_knees", "injury_back", "injury_neck", "injury_hips",
    "injury_other", "surgery", "medication", "notes", "photo",
]


def clear_member_form(key_prefix):
    for suffix in FORM_FIELD_SUFFIXES:
        st.session_state.pop(f"{key_prefix}_{suffix}", None)


if "show_add_member_form" not in st.session_state:
    st.session_state.show_add_member_form = False
if "editing_member_id" not in st.session_state:
    st.session_state.editing_member_id = None

if st.session_state.show_add_member_form:
    if st.button("← Back to list", key="cancel_add_member"):
        st.session_state.show_add_member_form = False
        st.rerun()

    st.subheader("Add New Member")
    data, photo_file = member_form("add")
    if data is not None:
        if data["mobile"]:
            duplicates = members_service.find_by_mobile(conn, data["mobile"])
            if duplicates:
                st.warning(f"{len(duplicates)} existing member(s) already use this mobile number.")
        if st.button("Save Member", key="save_new_member"):
            try:
                member_id = members_service.create_member(conn, data)
                save_uploaded_photo(member_id, photo_file, data)
                clear_member_form("add")
                st.session_state.show_add_member_form = False
                st.session_state.member_flash = f"Member '{data['first_name']}' saved."
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except Exception:
                report_unexpected_error()

elif st.session_state.editing_member_id is not None:
    member_id = st.session_state.editing_member_id
    m = members_service.get_member(conn, member_id)

    if st.button("← Back to list", key="cancel_edit_member"):
        st.session_state.editing_member_id = None
        st.rerun()

    st.subheader(f"Edit {m['first_name']} {m['surname'] or ''}")
    key_prefix = f"edit_{member_id}"
    edited, photo_file = member_form(key_prefix, existing=m)
    if edited is not None:
        col_save, col_toggle = st.columns(2)
        if col_save.button("Save Changes", key=f"save_{key_prefix}"):
            try:
                members_service.update_member(conn, member_id, edited)
                save_uploaded_photo(member_id, photo_file, edited)
                st.session_state.editing_member_id = None
                st.session_state.member_flash = "Updated."
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except Exception:
                report_unexpected_error()
        toggle_label = "Deactivate Member" if m["is_active"] else "Reactivate Member"
        if col_toggle.button(toggle_label, key=f"toggle_active_{member_id}"):
            ok, _ = safe_action(lambda: members_service.set_member_active(conn, member_id, not m["is_active"]))
            if ok:
                st.session_state.editing_member_id = None
                st.rerun()

else:
    if st.session_state.get("member_flash"):
        st.success(st.session_state.pop("member_flash"))

    col_title, col_add = st.columns([4, 1])
    if col_add.button("+ Add Member", key="show_add_member_button"):
        st.session_state.show_add_member_form = True
        st.rerun()

    col_search, col_search_btn = st.columns([4, 1], vertical_alignment="bottom")
    query = col_search.text_input("Search by name or mobile", key="member_search_query")
    col_search_btn.button("Search", key="member_search_button")
    show_inactive = st.checkbox("Show inactive members", key="member_show_inactive")

    MEMBERS_PAGE_SIZE = 20
    if "member_list_page" not in st.session_state:
        st.session_state.member_list_page = 1
    if st.session_state.get("member_list_last_query") != query:
        st.session_state.member_list_page = 1
        st.session_state.member_list_last_query = query

    results = members_service.search_members(conn, query, active_only=not show_inactive)
    total = len(results)
    total_pages = max(1, -(-total // MEMBERS_PAGE_SIZE))
    st.session_state.member_list_page = min(max(st.session_state.member_list_page, 1), total_pages)
    page = st.session_state.member_list_page
    start = (page - 1) * MEMBERS_PAGE_SIZE
    page_results = results[start:start + MEMBERS_PAGE_SIZE]

    plan_labels = {p["id"]: p["name"] for p in payments_service.list_plans(conn, active_only=False)}

    st.write(f"{total} member(s) found")
    if page_results:
        header = st.columns([3, 2, 2, 2, 1, 2])
        header[0].markdown("**Name**")
        header[1].markdown("**Phone**")
        header[2].markdown("**Plan**")
        header[3].markdown("**Payment**")
        header[4].markdown("**Edit**")
        header[5].markdown("**Active**")

    for m in page_results:
        status = payments_service.get_status(conn, m["id"])
        if status["status"] == "paid":
            badge = "🟢 Paid"
        elif status["status"] == "overdue":
            badge = "🔴 Overdue"
        else:
            badge = "⚪ No payment yet"

        row = st.columns([3, 2, 2, 2, 1, 2])
        row[0].write(f"{m['first_name']} {m['surname'] or ''}")
        row[1].write(m["mobile"])
        row[2].write(plan_labels.get(m["plan_id"], "—"))
        row[3].write(badge)
        if row[4].button("Edit", key=f"edit_button_{m['id']}"):
            st.session_state.editing_member_id = m["id"]
            st.rerun()
        toggle_label = "Deactivate" if m["is_active"] else "Reactivate"
        if row[5].button(toggle_label, key=f"toggle_active_{m['id']}"):
            ok, _ = safe_action(lambda member=m: members_service.set_member_active(conn, member["id"], not member["is_active"]))
            if ok:
                st.rerun()

    if total_pages > 1:
        col_prev, col_page, col_next = st.columns([1, 2, 1])
        if col_prev.button("← Previous", key="member_page_prev", disabled=page <= 1):
            st.session_state.member_list_page -= 1
            st.rerun()
        col_page.write(f"Page {page} of {total_pages}")
        if col_next.button("Next →", key="member_page_next", disabled=page >= total_pages):
            st.session_state.member_list_page += 1
            st.rerun()
