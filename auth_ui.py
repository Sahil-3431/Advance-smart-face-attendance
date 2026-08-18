import streamlit as st

from auth import (
    login_user,
    signup_user,
    change_password
)



# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Smart Face Attendance",
    page_icon="👤",
    layout="centered",
    initial_sidebar_state="collapsed"
)


# =========================================================
# PREMIUM AUTH CSS
# =========================================================

def load_auth_css():
    css_path = "assets/auth.css"
    try:
        with open(
            css_path,
            "r",
            encoding="utf-8"
        ) as file:
            css = file.read()
        st.markdown(
            f"<style>{css}</style>",
            unsafe_allow_html=True
        )
    except FileNotFoundError:
        st.error(f"Auth CSS file not found: {css_path}")

# =========================================================
# LOGIN PAGE
# =========================================================

def login_page():
    # =====================================================
    # BRAND HEADER
    # =====================================================

    st.markdown(
        """
        <div class="auth-brand">
            <div class="brand-logo">
                <div class="brand-icon">
                    👤
                </div>
                <div class="brand-title">
                    <span class="purple">Smart Face</span>
                    Attendance
                </div>
            </div>
            <div class="brand-subtitle">
                AI-Powered Attendance Management System
            </div>
            <div class="brand-divider"></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # =====================================================
    # REAL STREAMLIT CONTAINER
    # =====================================================

    with st.container(border=True):
        st.markdown(
            """
            <div class="auth-welcome">
                <h1>
                    Welcome Back 👋
                </h1>
                <p>
                    Sign in to access your attendance dashboard.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # =================================================
        # USERNAME
        # =================================================

        identifier = st.text_input(
            "👤 Username or Email",
            placeholder="Enter username or email",
            key="login_identifier"
        )

        # =================================================
        # PASSWORD
        # =================================================

        password = st.text_input(
            "🔒 Password",
            type="password",
            placeholder="Enter your password",
            key="login_password"
        )

        # =================================================
        # LOGIN
        # =================================================

        login_clicked = st.button(
            "🔐  Sign In",
            type="primary",
            use_container_width=True
        )

        if login_clicked:
            if not identifier or not password:
                st.error("Please enter username/email and password.")
            else:
                user = login_user(identifier,password)
                if user:
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = user
                    st.session_state["auth_page"] = "login"
                    username = user.get("username",identifier)
                    st.success(f"Welcome back, {username}!")
                    st.rerun()
                else:
                    st.error("Invalid username/email or password.")

        # =================================================
        # SIGNUP DIVIDER
        # =================================================

        st.markdown(
            """
            <div class="account-divider">
                Don't have an account?
            </div>
            """,
            unsafe_allow_html=True
        )

        # =================================================
        # CREATE ACCOUNT
        # =================================================

        if st.button(
            "👤  Create New Account",
            use_container_width=True
        ):
            st.session_state[
                "auth_page"
            ] = "signup"
            st.rerun()

    # =====================================================
    # SECURITY NOTE
    # =====================================================

    st.markdown(
        """
        <div class="security-note">
            <div class="security-icon">
                🛡️
            </div>
            <div>
                Your account credentials are securely protected
                using <strong>advanced password hashing.</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
# =========================================================
# SIGNUP PAGE
# =========================================================

def signup_page():
    st.markdown(
        """
        <div class="auth-brand">
            <div class="brand-logo">
                <div class="brand-icon">
                    ✨
                </div>
                <div class="brand-title">
                    <span class="purple">Smart Face</span>
                    Attendance
                </div>
            </div>
            <div class="brand-subtitle">
                AI-Powered Attendance Management System
            </div>
            <div class="brand-divider"></div>
        </div>
        """,
        unsafe_allow_html=True
    )
    with st.container(border=True):
        st.markdown(
            """
            <div class="auth-welcome">
                <h1>
                    Create Your Account ✨
                </h1>
                <p>
                    Start managing attendance smarter and faster.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        username = st.text_input(
            "👤 Username",
            placeholder="Choose a username",
            key="signup_username"
        )
        email = st.text_input(
            "📧 Email Address",
            placeholder="name@example.com",
            key="signup_email"
        )
        password = st.text_input(
            "🔒 Password",
            type="password",
            placeholder="Minimum 8 characters",
            key="signup_password"
        )
        confirm_password = st.text_input(
            "🔒 Confirm Password",
            type="password",
            placeholder="Re-enter your password",
            key="signup_confirm_password"
        )
        signup_clicked = st.button(
            "🚀  Create Account",
            type="primary",
            use_container_width=True
        )
        if signup_clicked:
            success, message = signup_user(
                username,
                email,
                password,
                confirm_password
            )
            if success:
                st.success(message)
                st.session_state["auth_page"] = "login"
                st.rerun()
            else:
                st.error(message)

        st.markdown(
            """
            <div class="account-divider">
                Already have an account?
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button(
            "←  Back to Sign In",
            use_container_width=True
        ):
            st.session_state["auth_page"] = "login"
            st.rerun()

# =========================================================
# AUTH ROUTER
# =========================================================

def show_authentication():
    load_auth_css()
    # =====================================================
    # DEFAULT AUTH PAGE
    # =====================================================
    if "auth_page" not in st.session_state:
        st.session_state["auth_page"] = "login"
    # =====================================================
    # ROUTER
    # =====================================================
    if st.session_state["auth_page"] == "signup":
        signup_page()
    else:
        login_page()

# =========================================================
# CHANGE PASSWORD PAGE
# =========================================================

def change_password_page():
    # =====================================================
    # BRAND
    # =====================================================

    st.markdown(
        """
        <div class="auth-brand">
            <div class="brand-logo">
                <div class="brand-icon">
                    🔐
                </div>
                <div class="brand-title">
                    <span class="purple">Change</span>
                    Password
                </div>
            </div>
            <div class="brand-subtitle">
                Securely update your account password
            </div>
            <div class="brand-divider"></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # =====================================================
    # CARD
    # =====================================================

    with st.container(border=True):
        st.markdown(
            """
            <div class="auth-welcome">
                <h1>
                    🔐 Change Password
                </h1>
                <p>
                    Verify your current credentials before
                    creating a new password.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # =================================================
        # USERNAME / EMAIL
        # =================================================

        identifier = st.text_input(
            "👤 Username or Email",
            placeholder="Enter your username or email",
            key="change_identifier"
        )

        # =================================================
        # CURRENT PASSWORD
        # =================================================

        current_password = st.text_input(
            "🔒 Current Password",
            type="password",
            placeholder="Enter your current password",
            key="change_current_password"
        )

        # =================================================
        # NEW PASSWORD
        # =================================================

        new_password = st.text_input(
            "🔑 New Password",
            type="password",
            placeholder="Enter your new password",
            key="change_new_password"
        )

        # =================================================
        # CONFIRM PASSWORD
        # =================================================

        confirm_password = st.text_input(
            "🔑 Confirm New Password",
            type="password",
            placeholder="Re-enter your new password",
            key="change_confirm_password"
        )
        st.caption(
            "Password must contain at least 8 characters, "
            "one uppercase letter, one lowercase letter "
            "and one number."
        )
        st.markdown("")

        # =================================================
        # BUTTONS
        # =================================================

        col1,col2 = st.columns(2)
        with col1:
            change_clicked = st.button(
                "🔐 Change Password",
                type="primary",
                use_container_width=True
            )
        with col2:
            cancel_clicked = st.button(
                "← Back",
                use_container_width=True
            )

        # =================================================
        # BACK
        # =================================================

        if cancel_clicked:
            st.session_state["page"] = "dashboard"
            st.rerun()

        # =================================================
        # CHANGE PASSWORD
        # =================================================

        if change_clicked:
            success, message = change_password(
                identifier,
                current_password,
                new_password,
                confirm_password
            )
            if success:
                st.success(message)
                st.info(
                    "For security, please login again "
                    "using your new password."
                )

                # -----------------------------------------
                # CLEAR AUTH SESSION
                # -----------------------------------------

                st.session_state["authenticated"] = False
                st.session_state.pop("user",None)
                st.session_state["auth_page"] = "login"
                st.session_state.pop("page",None)
                st.rerun()
            else:
                st.error(message)