import streamlit as st
import pandas as pd
import cv2
from auth_ui import show_authentication
from streamlit_webrtc import (
    webrtc_streamer,
    WebRtcMode
)
from config import (
    APP_TITLE,
    APP_ICON,
    DEVELOPER_NAME
)
from database import *

from face_engine import(
    load_models,
    detect_faces,
    get_embedding,
    find_registered_person
)
from utils import (
    embedding_to_bytes,
    draw_face_box
)
from webcam import (
    RegistrationProcessor,
    AttendanceProcessor,
    latest_frame,
    frame_lock
)
from theme import (
    load_main_css,
    initialize_theme,
    theme_toggle,
    apply_theme
)
from analytics import (
    attendance_dataframe,
    calculate_kpis,
    daily_attendance_trend,
    department_attendance,
    person_performance,
    hourly_attendance,
    recent_attendance,
    dataframe_to_csv
)
from auth import *



# =====================================================
# PAGE
# =====================================================

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide"
)

# =====================================================
# PREMIUM THEME
# =====================================================

load_main_css()
initialize_theme()
apply_theme()

# =====================================================
# DATABASE
# =====================================================

init_database()

# =====================================================
# INITIAL ADMIN SETUP
# =====================================================

from admin_setup import create_initial_admin

try:
    create_initial_admin()
except Exception:
    pass

# =====================================================
# AUTHENTICATION
# =====================================================

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    show_authentication()
    st.stop()

# =====================================================
# LOAD MODELS
# =====================================================

@st.cache_resource
def load_face_models():
    return load_models()

detector, recognizer = load_face_models()

# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:
    st.markdown(
        """
        <div class="app-brand">
            <div class="app-brand-icon">
                👤
            </div>
            <div>
                <div class="app-brand-title">
                    Smart Face
                </div>
                <div class="app-brand-subtitle">
                    ATTENDANCE SYSTEM
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ---------------------------------------------
    # USER
    # ---------------------------------------------

    current_user = st.session_state.get("user",{})
    username = current_user.get("username","User")
    role = current_user.get("role","user")
    st.markdown(
        f"""
        <div class="sidebar-user">
            <div class="sidebar-user-name">
                👋 {username}
            </div>
            <div class="sidebar-user-role">
                {role.title()} Account
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ---------------------------------------------
    # NAVIGATION
    # ---------------------------------------------

    st.caption("WORKSPACE")

    # =====================================================
    # ROLE BASED NAVIGATION
    # =====================================================

    navigation = ["🏠 Dashboard"]
    if has_permission(current_user,"register_person"):
        navigation.append("👤 Register Person")
    if has_permission(current_user,"live_attendance"):
        navigation.append("📸 Live Attendance")
    if has_permission(current_user,"attendance_records"):
        navigation.append("📋 Attendance Records")
    if has_permission(current_user,"registered_people"):
        navigation.append("👥 Registered People")
    if has_permission(current_user,"user_management"):
        navigation.append("👨‍💼 User Management")
    if has_permission(current_user,"audit_logs"):
        navigation.append("📜 Audit Logs")

    navigation.append("🔐 Change Password")

    menu = st.radio(
        "Navigation",
        navigation,
        label_visibility="collapsed"
    )

    # ---------------------------------------------
    # THEME
    # ---------------------------------------------

    theme_toggle()

    # ---------------------------------------------
    # LOGOUT
    # ---------------------------------------------

    if st.button("🚪 Logout",use_container_width=True):
        from auth import logout_user
        logout_user(username)
        st.session_state["authenticated"] = False
        st.session_state["user"] = {}
        st.session_state["auth_page"] = "login"
        st.rerun()
    st.divider()
    st.caption("Smart Face Recognition Attendance")
    st.caption(f"Developed by {DEVELOPER_NAME}")
# =====================================================
# DASHBOARD
# =====================================================

if menu == "🏠 Dashboard":
    people = get_people()
    attendance = get_attendance()
    # =====================================================
    # ANALYTICS DATA
    # =====================================================

    attendance_df = attendance_dataframe(attendance)
    if people:
        people_df = pd.DataFrame(
            people,
            columns=[
                "id",
                "person_id",
                "name",
                "department",
                "embedding",
                "created_at"
            ]
        )
    else:
        people_df = pd.DataFrame(
            columns=[
                "id",
                "person_id",
                "name",
                "department",
                "embedding",
                "created_at"
            ]
        )
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    today_attendance = [
        row
        for row in attendance
        if row[2] == today
    ]
    total_people = len(people)
    today_present = len(today_attendance)
    total_attendance = len(attendance)
    if total_people > 0:
        attendance_rate = (
            today_present /
            total_people
        ) * 100
    else:
        attendance_rate = 0

    # =================================================
    # HEADER
    # =================================================

    st.markdown(
        f"""
        <div class="page-header">
            <div>
                <div class="page-title">
                    Dashboard
                </div>
                <div class="page-subtitle">
                    Monitor attendance and manage
                    your smart recognition system.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # =================================================
    # HERO
    # =================================================

    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-title">
                Welcome back, {username} 👋
            </div>
            <div class="hero-text">
                Your AI-powered attendance
                system is ready.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">
                📅 Analytics Filters
            </div>
            <div class="section-subtitle">
                Select a period to analyze attendance.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    from datetime import date, timedelta
    today = date.today()
    default_start = (today - timedelta(days=6))
    filter_col1,filter_col2 = st.columns(2)
    with filter_col1:
        start_date = st.date_input(
            "Start Date",
            value=default_start,
            key="analytics_start_date"
        )
    with filter_col2:
        end_date = st.date_input(
            "End Date",
            value=today,
            key="analytics_end_date"
        )

    departments = []
    if not people_df.empty:
        departments = sorted(
            people_df["department"]
            .fillna("Not Assigned")
            .replace("", "Not Assigned")
            .unique()
            .tolist()
        )
    selected_department = st.selectbox(
        "Department",
        ["All Departments"] + departments,
        key="analytics_department"
    )

    filtered_people = people_df.copy()
    filtered_attendance = attendance_df.copy()
    if (
        selected_department!= "All Departments"):
        filtered_people = filtered_people[
            filtered_people["department"]
            .fillna("Not Assigned")
            .replace("", "Not Assigned")
            == selected_department
        ]
        allowed_ids = set(filtered_people["person_id"])
        filtered_attendance = (
            filtered_attendance[
                filtered_attendance["person_id"]
                .isin(allowed_ids)
            ]
        )
    if not filtered_attendance.empty:
        filtered_attendance = (
            filtered_attendance[
                (
                    filtered_attendance["date"]
                    >= pd.Timestamp(start_date)
                )
                &
                (
                    filtered_attendance["date"]
                    <= pd.Timestamp(end_date)
                )
            ]
        )

    # =================================================
    # KPI CARDS
    # =================================================

    kpis = calculate_kpis(filtered_people,filtered_attendance)

    col1,col2,col3,col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-icon">
                    👥
                </div>
                <div class="metric-label">
                    Registered People
                </div>
                <div class="metric-value">
                    {kpis["total_people"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-icon">
                    🟢
                </div>
                <div class="metric-label">
                    Today's Present
                </div>
                <div class="metric-value">
                    {kpis["today_present"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-icon">
                    🔴
                </div>
                <div class="metric-label">
                    Today's Absent
                </div>
                <div class="metric-value">
                    {kpis["today_absent"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-icon">
                    📈
                </div>
                <div class="metric-label">
                    Attendance Rate
                </div>
                <div class="metric-value">
                    {kpis["attendance_rate"]:.1f}%
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
            """
            <div class="section-card">
                <div class="section-title">
                    📈 Attendance Trend
                </div>
                <div class="section-subtitle">
                    Daily unique attendance over the selected period.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    trend_df = daily_attendance_trend(
            filtered_attendance,
            start_date,
            end_date
        )
    if not trend_df.empty:
        trend_df["date"] = (
            trend_df["date"]
            .dt.strftime("%d %b")
        )
        st.line_chart(
            trend_df.set_index("date")[
                "present"
            ],
            use_container_width=True
        )
    else:
        st.info(
            "No attendance data available "
            "for the selected period."
        )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">
                    🏢 Department Performance
                </div>
                <div class="section-subtitle">
                    Attendance distribution by department.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        department_df = department_attendance(filtered_people,filtered_attendance)
        if not department_df.empty:
            chart_df = (
                department_df
                .set_index("department")
                ["attendance_records"]
            )
            st.bar_chart(chart_df,use_container_width=True)
        else:
            st.info("No department data available.")
    with col2:
        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">
                    🕐 Attendance Timing
                </div>
                <div class="section-subtitle">
                    Shows when people usually mark attendance.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        hourly_df = hourly_attendance(filtered_attendance)
        if not hourly_df.empty:
            chart_df = (
                hourly_df
                .set_index("hour")
                ["attendance"]
            )
            st.bar_chart(chart_df,use_container_width=True)
        else:
            st.info("No timing data available.")
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">
                🏆 Attendance Leaders
            </div>
            <div class="section-subtitle">
                People with the highest attendance records.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    performance_df = person_performance(filtered_people,filtered_attendance)
    if not performance_df.empty:
        performance_df = (
            performance_df
            .head(10)
            .rename(
                columns={
                    "person_id": "Person ID",
                    "name": "Name",
                    "department": "Department",
                    "attendance_days":
                        "Attendance Days"
                }
            )
        )
        st.dataframe(performance_df,use_container_width=True,hide_index=True)
    else:
        st.info("No performance data available.")

    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">
                🕘 Recent Activity
            </div>
            <div class="section-subtitle">
                Latest attendance records.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    recent_df = recent_attendance(filtered_attendance,limit=10)
    if not recent_df.empty:
        recent_display = recent_df.copy()
        recent_display["date"] = (
            recent_display["date"]
            .dt.strftime("%d %b %Y")
        )
        recent_display.columns = [
            "Person ID",
            "Name",
            "Date",
            "Time",
            "Status"
        ]
        st.dataframe(recent_display,use_container_width=True,hide_index=True)
    else:
        st.info("No recent attendance activity.")

    st.divider()
    export_df = filtered_attendance.copy()
    if not export_df.empty:
        export_df["date"] = (
            export_df["date"]
            .dt.strftime("%Y-%m-%d")
        )
    csv_data = dataframe_to_csv(export_df)
    st.download_button(
        label="📥 Download Attendance CSV",
        data=csv_data,
        file_name=(
            f"attendance_"
            f"{start_date}_"
            f"to_"
            f"{end_date}.csv"
        ),
        mime="text/csv",
        use_container_width=True
    )

    # =================================================
    # RECENT ATTENDANCE
    # =================================================

    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">
                Recent Attendance
            </div>
            <div class="section-subtitle">
                Latest attendance activity
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    if attendance:
        df = pd.DataFrame(
            attendance,
            columns=[
                "Person ID",
                "Name",
                "Date",
                "Time",
                "Status"
            ]
        )
        st.dataframe(
            df.head(10),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No attendance records available yet.")
# =====================================================
# REGISTER PERSON
# =====================================================

elif menu == "👤 Register Person":
    st.markdown(
            """
            <div class="page-header">
                <div>
                    <div class="page-title">
                        Register Person
                    </div>
                    <div class="page-subtitle">
                        Add a new person to the facial
                        recognition database.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    col1,col2 = st.columns([1, 1.5])

    # =================================================
    # PERSON DETAILS
    # =================================================

    with col1:
        person_id = st.text_input("Roll No.",placeholder="Enter Your Roll No.")
        name = st.text_input("Full Name",placeholder="Enter your Name")
        department = st.text_input("Department",placeholder="Your Department")

    # =================================================
    # LIVE CAMERA
    # =================================================

    with col2:
        st.subheader("📷 Live Webcam")
        webrtc_streamer(
            key="register",
            mode=WebRtcMode.SENDRECV,
            media_stream_constraints={
                "video": True,
                "audio": False
            },
            video_processor_factory=(
                RegistrationProcessor
            ),
            async_processing=True
        )
    st.divider()

    # =================================================
    # CAPTURE FACE
    # =================================================

    if st.button("📸 Capture Current Face",type="primary",use_container_width=True):
        with frame_lock:
            if latest_frame is None:
                captured = None
            else:
                captured = latest_frame.copy()
        if captured is None:
            st.error(
                "❌ Camera start nahi hua. "
                "Pehle START button dabao."
            )
        else:
            faces = detect_faces(detector,captured)

            # -----------------------------------------
            # NO FACE
            # -----------------------------------------

            if len(faces) == 0:
                st.error("❌ Face detect nahi hua.")

            # -----------------------------------------
            # MULTIPLE FACES
            # -----------------------------------------

            elif len(faces) > 1:
                st.error(
                    "❌ Multiple faces detected. "
                    "Sirf ek person camera ke saamne ho."
                )

            # -----------------------------------------
            # ONE FACE
            # -----------------------------------------

            else:
                face = faces[0]

                # -------------------------------------
                # CREATE EMBEDDING
                # -------------------------------------

                embedding = get_embedding(recognizer,captured,face)

                # -------------------------------------
                # CHECK EXISTING FACE
                # -------------------------------------

                people = get_people()
                existing_person = (
                    find_registered_person(
                        recognizer,
                        embedding,
                        people
                    )
                )
                preview = captured.copy()

                # =====================================
                # FACE ALREADY REGISTERED
                # =====================================

                if existing_person:
                    existing_name = (existing_person["name"])
                    existing_id = (existing_person["person_id"])
                    label = (
                        f"ALREADY REGISTERED: "
                        f"{existing_name}"
                    )
                    preview = draw_face_box(
                        preview,
                        face,
                        label,
                        False
                    )
                    preview = cv2.cvtColor(preview,cv2.COLOR_BGR2RGB)
                    st.image(
                        preview,
                        caption="Face Already Registered",
                        use_container_width=True
                    )
                    st.error(
                        f"⚠️ This face is already registered "
                        f"as {existing_name} "
                        f"({existing_id})."
                    )
                    st.warning(
                        "Is person ko dobara register "
                        "nahi kiya ja sakta."
                    )

                    # Important:
                    # Don't save this face
                    st.session_state["captured_face"] = None
                    st.session_state["captured_face_data"] = None

                # =====================================
                # NEW FACE
                # =====================================

                else:
                    label = "NEW FACE - READY TO REGISTER"
                    preview = draw_face_box(
                        preview,
                        face,
                        label,
                        True
                    )

                    preview = cv2.cvtColor(preview,cv2.COLOR_BGR2RGB)
                    st.image(
                        preview,
                        caption="New Face Detected",
                        use_container_width=True
                    )
                    st.success("✅ This face is not registered.")

                    # Save captured frame

                    st.session_state["captured_face"] = captured
                    st.session_state["captured_face_data"] = face

                    # Save embedding
                    st.session_state["captured_embedding"] = embedding

    # =================================================
    # REGISTER BUTTON
    # =================================================

    captured_face = st.session_state.get("captured_face")
    captured_face_data = st.session_state.get("captured_face_data")
    captured_embedding = st.session_state.get("captured_embedding")
    if (
        captured_face is not None
        and captured_face_data is not None
        and captured_embedding is not None
    ):
        st.divider()
        st.success("Face ready. Ab details verify karke Register Person dabao.")
        if st.button("💾 Register Person",type="primary",use_container_width=True):
            # -----------------------------------------
            # VALIDATION
            # -----------------------------------------

            if not person_id.strip():
                st.error("❌ Person ID enter karo.")
            elif not name.strip():
                st.error("❌ Name enter karo.")
            elif person_exists(person_id.strip()):
                st.error("❌ This Person ID already exists.")
            else:
                # -------------------------------------
                # SAVE TO DATABASE
                # -------------------------------------

                embedding_bytes = (
                    embedding_to_bytes(
                        captured_embedding
                    )
                )
                add_person(
                    person_id.strip(),
                    name.strip(),
                    department.strip(),
                    embedding_bytes
                )
                add_audit_log(
                    username,
                    "REGISTER_PERSON",
                    (
                        f"Registered person: "
                        f"{name.strip()} "
                        f"({person_id.strip()})"
                    )
                )
                st.success(f"🎉 {name} successfully registered!")
                st.balloons()

                # -------------------------------------
                # CLEAR SESSION
                # -------------------------------------

                st.session_state["captured_face"] = None
                st.session_state["captured_face_data"] = None
                st.session_state["captured_embedding"] = None

# =====================================================
# USER MANAGEMENT
# =====================================================

elif menu == "👨‍💼 User Management":
    if not has_permission(current_user,"user_management"):
        st.error("🚫 Access denied.")
        st.stop()
    st.markdown(
        """
        <div class="page-header">
            <div>
                <div class="page-title">
                    User Management
                </div>
                <div class="page-subtitle">
                    Manage application users,
                    roles and account access.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    users = get_users()
    if not users:
        st.info("No users found.")
    else:

        # =============================================
        # USER TABLE
        # =============================================

        users_df = pd.DataFrame(
            users,
            columns=[
                "ID",
                "Username",
                "Email",
                "Role",
                "Active",
                "Created At",
                "Last Login"
            ]
        )
        users_df["Status"] = (
            users_df["Active"]
            .map({
                1: "🟢 Active",
                0: "🔴 Disabled"
            })
        )
        st.dataframe(
            users_df[
                [
                    "ID",
                    "Username",
                    "Email",
                    "Role",
                    "Status",
                    "Created At",
                    "Last Login"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )
        st.divider()

        # =============================================
        # SELECT USER
        # =============================================

        user_options = {
            f"{row[1]} — {row[3]}": row
            for row in users
        }
        selected_label = st.selectbox(
            "Select User",
            list(user_options.keys()),
            key="manage_user_select"
        )
        selected_user = user_options[selected_label]
        selected_id = selected_user[0]
        selected_username = selected_user[1]
        selected_role = selected_user[3]
        selected_active = selected_user[4]
        st.markdown("### Account Actions")
        col1,col2 = st.columns(2)

        # =============================================
        # ACTIVATE
        # =============================================

        with col1:
            if st.button("🟢 Activate User",use_container_width=True):
                if set_user_status(selected_id,True):
                    add_audit_log(
                        username,
                        "ACTIVATE_USER",
                        f"Activated user: {selected_username}"
                    )
                    st.success(f"{selected_username} activated.")
                    st.rerun()

        # =============================================
        # DISABLE
        # =============================================

        with col2:
            if st.button("🔴 Disable User",use_container_width=True):
                if (selected_username== username):
                    st.warning(
                        "You cannot disable "
                        "your own account."
                    )
                else:
                    if set_user_status(selected_id,False):
                        add_audit_log(
                            username,
                            "DISABLE_USER",
                            f"Disabled user: {selected_username}"
                        )
                        st.success(f"{selected_username} disabled.")
                        st.rerun()

        # =============================================
        # CHANGE ROLE
        # =============================================

        st.markdown("### Change User Role")
        new_role = st.selectbox(
            "Select Role",
            ["user", "admin"],
            index=(
                0
                if selected_role == "user"
                else 1
            ),
            key="manage_user_role"
        )
        if st.button("🔄 Update Role",type="primary",use_container_width=True):
            if (
                selected_username
                == username
                and new_role != selected_role
            ):
                st.warning(
                    "You cannot change "
                    "your own role."
                )
            else:
                if set_user_role(selected_id,new_role):
                    add_audit_log(
                        username,
                        "CHANGE_ROLE",
                        (
                            f"Changed {selected_username} "
                            f"role from {selected_role} "
                            f"to {new_role}"
                        )
                    )
                    st.success("User role updated successfully.")
                    st.rerun()

        # =============================================
        # DELETE USER
        # =============================================

        st.divider()
        st.markdown("### Danger Zone")
        if st.button("🗑️ Delete Selected User",type="secondary",use_container_width=True):
            if (selected_username== username):
                st.warning(
                    "You cannot delete "
                    "your own account."
                )
            else:
                st.session_state["confirm_delete_app_user"] = selected_id
        if (
            st.session_state.get(
                "confirm_delete_app_user"
            )
            == selected_id
        ):
            st.warning(
                f"Are you sure you want to "
                f"delete {selected_username}?"
            )
            c1,c2 = st.columns(2)
            with c1:
                if st.button("✅ Yes, Delete",type="primary",key="confirm_delete_app_user_btn"):
                    if delete_user(selected_id):
                        add_audit_log(
                            username,
                            "DELETE_USER",
                            f"Deleted user: {selected_username}"
                        )
                        st.session_state["confirm_delete_app_user"] = None
                        st.success("User deleted successfully.")
                        st.rerun()
            with c2:
                if st.button("❌ Cancel",key="cancel_delete_app_user_btn"):
                    st.session_state["confirm_delete_app_user"] = None
                    st.rerun()


# =====================================================
# LIVE ATTENDANCE
# =====================================================

elif menu == "📸 Live Attendance":
    st.markdown(
        """
        <div class="page-header">
            <div>
                <div class="page-title">
                    Live Attendance
                </div>
                <div class="page-subtitle">
                    Real-time AI face recognition
                    and automatic attendance.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    people = get_people()
    if not people:
        st.warning("⚠️ No registered people.")
        st.info("First register a person.")
    else:
        st.success(f"🟢 {len(people)} registered people available.")
        st.write(
            "Start the camera and look at it. "
            "Recognition + attendance will happen automatically."
        )
        webrtc_streamer(
            key="attendance",
            mode=WebRtcMode.SENDRECV,
            media_stream_constraints={
                "video": True,
                "audio": False
            },
            video_processor_factory=lambda:
                AttendanceProcessor(
                    detector,
                    recognizer
                ),
            async_processing=True
        )


# =====================================================
# AUDIT LOGS
# =====================================================

elif menu == "📜 Audit Logs":
    # =============================================
    # PERMISSION CHECK
    # =============================================

    if not has_permission(current_user,"audit_logs"):
        st.error("🚫 Access denied.")
        st.stop()

    # =============================================
    # PAGE HEADER
    # =============================================
    
    st.markdown("## 📜 Audit Logs")
    st.caption("Monitor important activities performed by system users.")

    # =============================================
    # LOAD LOGS
    # =============================================

    logs = get_audit_logs(limit=200)
    if not logs:
        st.info("No audit activity found.")
    else:
        logs_df = pd.DataFrame(
            logs,
            columns=[
                "User",
                "Action",
                "Details",
                "Timestamp"
            ]
        )

        # =========================================
        # FILTERS
        # =========================================

        col1,col2 = st.columns(2)
        with col1:
            users = [
                "All Users"
            ] + sorted(
                logs_df["User"]
                .dropna()
                .unique()
                .tolist()
            )
            selected_user = st.selectbox(
                "👤 User",
                users,
                key="audit_user_filter"
            )
        with col2:
            actions = [
                "All Actions"
            ] + sorted(
                logs_df["Action"]
                .dropna()
                .unique()
                .tolist()
            )
            selected_action = st.selectbox(
                "⚡ Action",
                actions,
                key="audit_action_filter"
            )

        # =========================================
        # APPLY FILTERS
        # =========================================

        filtered_logs = logs_df.copy()
        if selected_user != "All Users":
            filtered_logs = filtered_logs[
                filtered_logs["User"]
                == selected_user
            ]
        if selected_action != "All Actions":
            filtered_logs = filtered_logs[
                filtered_logs["Action"]
                == selected_action
            ]

        # =========================================
        # KPI CARDS
        # =========================================

        total_logs = len(filtered_logs)
        unique_users = (
            filtered_logs["User"]
            .nunique()
        )
        unique_actions = (
            filtered_logs["Action"]
            .nunique()
        )
        c1,c2,c3 = st.columns(3)
        with c1:
            st.metric(
                "Total Activities",
                total_logs
            )
        with c2:
            st.metric(
                "Active Users",
                unique_users
            )
        with c3:
            st.metric(
                "Action Types",
                unique_actions
            )
        st.divider()

        # =========================================
        # LOG TABLE
        # =========================================

        st.dataframe(
            filtered_logs,
            use_container_width=True,
            hide_index=True,
            height=500
        )


# =====================================================
# ATTENDANCE RECORDS
# =====================================================

elif menu == "📋 Attendance Records":
    st.markdown(
        """
        <div class="page-header">
            <div>
                <div class="page-title">
                    Attendance Records
                </div>
                <div class="page-subtitle">
                    Search, review and export attendance
                    history.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    attendance = get_attendance()
    if not attendance:
        st.info("No attendance records found.")

    else:
        # =================================================
        # SEARCH
        # =================================================

        search = st.text_input("🔎 Search Attendance",placeholder="Search by Roll No or Name...")
        search_text = search.lower().strip()
        filtered_attendance = []
        for row in attendance:
            person_id = str(row[0]).lower()

            name = str(row[1]).lower()

            if (
                search_text == ""
                or search_text in person_id
                or search_text in name
            ):
                filtered_attendance.append(row)

        st.write(
            f"Showing {len(filtered_attendance)} "
            f"of {len(attendance)} records"
        )

        # =================================================
        # TABLE
        # =================================================

        df = pd.DataFrame(
            filtered_attendance,
            columns=[
                "Person ID",
                "Name",
                "Date",
                "Time",
                "Status"
            ]
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        # =================================================
        # DELETE INDIVIDUAL ATTENDANCE
        # =================================================

        st.divider()
        st.subheader("🗑️ Delete Attendance")
        if filtered_attendance:
            options = []
            for row in filtered_attendance:
                options.append(
                    f"{row[1]} | "
                    f"{row[0]} | "
                    f"{row[2]} | "
                    f"{row[3]}"
                )
            selected = st.selectbox("Select attendance record",options)
            selected_index = options.index(selected)
            selected_record = (filtered_attendance[selected_index])
            selected_person_id = (selected_record[0])
            selected_date = (selected_record[2])
            if st.button("🗑️ Delete Selected Attendance",type="secondary"):
                delete_attendance(selected_person_id,selected_date)
                add_audit_log(
                    username,
                    "DELETE_ATTENDANCE",
                    (
                        f"Deleted attendance for "
                        f"{selected_person_id} "
                        f"on {selected_date}"
                    )
                )
                st.success("Attendance deleted successfully.")
                st.rerun()

        # =================================================
        # CLEAR ALL
        # =================================================

        st.divider()
        st.subheader("⚠️ Danger Zone")
        if st.button("🗑️ Delete ALL Attendance",type="secondary"):
            st.session_state["confirm_clear_attendance"] = True

        if st.session_state.get("confirm_clear_attendance",False):
            st.error(
                "This will permanently delete "
                "ALL attendance records."
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⚠️ Yes, Delete Everything",type="primary"):
                    clear_all_attendance()
                    add_audit_log(
                        username,
                        "CLEAR_ALL_ATTENDANCE",
                        "Deleted all attendance records."
                    )
                    st.session_state["confirm_clear_attendance"] = False
                    st.success("All attendance deleted.")
                    st.rerun()
            with col2:
                if st.button("Cancel"):
                    st.session_state["confirm_clear_attendance"] = False
                    st.rerun()

        # =================================================
        # CSV DOWNLOAD
        # =================================================

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "⬇️ Download CSV",
            csv,
            "attendance.csv",
            "text/csv"
        )

# =====================================================
# REGISTERED PEOPLE
# =====================================================

elif menu == "👥 Registered People":
    st.markdown(
        """
        <div class="page-header">
            <div>
                <div class="page-title">
                    Registered People
                </div>
                <div class="page-subtitle">
                    Manage people registered in the
                    face recognition system.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    people = get_people()
    if not people:
        st.info("No registered people found.")
    else:
        # =================================================
        # SEARCH
        # =================================================

        search = st.text_input("🔎 Search Person",placeholder="Search by Roll No or Name...")

        # =================================================
        # FILTER
        # =================================================

        filtered_people = []
        for person in people:
            person_id = str(person[1]).lower()
            name = str(person[2]).lower()
            search_text = search.lower().strip()
            if (
                search_text == ""
                or search_text in person_id
                or search_text in name
            ):
                filtered_people.append(person)
        # =================================================
        # RESULT COUNT
        # =================================================

        st.write(
            f"Showing {len(filtered_people)} "
            f"of {len(people)} users"
        )

        # =================================================
        # USERS
        # =================================================

        for person in filtered_people:
            person_id = person[1]
            name = person[2]
            department = person[3]
            created_at = person[5]
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div class="section-card">
                        <div class="section-title">
                            {name}
                        </div>
                        <div class="section-subtitle">
                            ID: {person_id} • {department}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                col1,col2,col3,col4 = st.columns([2, 3, 2, 1])
                with col1:
                    st.write(f"**ID:** {person_id}")
                with col2:
                    st.write(f"**Name:** {name}")
                with col3:
                    st.write(
                        f"**Department:** "
                        f"{department}"
                    )
                with col4:
                    delete_key = (f"delete_user_{person_id}")
                    if st.button("🗑️ Delete",key=delete_key):
                        st.session_state["confirm_delete_user"] = person_id

                # =========================================
                # CONFIRM DELETE
                # =========================================

                if (st.session_state.get("confirm_delete_user")== person_id):
                    st.warning(
                        f"⚠️ Are you sure you want "
                        f"to delete {name} ({person_id})?"
                    )
                    st.write(
                        "This will also delete "
                        "all attendance records of this user."
                    )
                    confirm_col1, confirm_col2 = st.columns(2)
                    with confirm_col1:
                        if st.button(
                            "✅ Yes, Delete",
                            key=f"confirm_{person_id}",
                            type="primary"
                        ):
                            delete_person(person_id)
                            add_audit_log(
                                username,
                                "DELETE_PERSON",
                                (
                                    f"Deleted person: "
                                    f"{name} ({person_id})"
                                )
                            )
                            st.session_state["confirm_delete_user"] = None
                            st.success(f"{name} deleted successfully.")
                            st.rerun()
                    with confirm_col2:
                        if st.button("❌ Cancel",key=f"cancel_{person_id}"):
                            st.session_state["confirm_delete_user"] = None
                            st.rerun()

# ==========================
# Change Password
# ==========================

elif menu == "🔐 Change Password":
    from auth_ui import change_password_page
    change_password_page()