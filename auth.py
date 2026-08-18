import re
from database import (
    create_user,
    authenticate_user as db_authenticate_user,
    add_audit_log,
    get_current_time,
    get_connection,
    get_users,
    set_user_status,
    set_user_role,
    delete_user,
    get_audit_logs,
    get_user_security_data,
    update_user_password,
    hash_password,
    verify_password
)

# =====================================================
# ROLE CHECK
# =====================================================

def is_admin(user):
    if not user:
        return False
    return (
        user.get("role", "").lower()
        == "admin"
    )

def is_user(user):
    if not user:
        return False
    return (
        user.get("role", "").lower()
        == "user"
    )

# =====================================================
# PERMISSIONS
# =====================================================

PERMISSIONS = {
    "admin": {
        "dashboard",
        "register_person",
        "live_attendance",
        "attendance_records",
        "registered_people",
        "user_management",
        "audit_logs"
    },
    "user": {
        "dashboard",
        "live_attendance",
        "attendance_records"
    }
}

# =====================================================
# PERMISSION CHECK
# =====================================================

def has_permission(user,permission):
    if not user:
        return False
    role = user.get(
        "role",
        "user"
    ).lower()
    return permission in (
        PERMISSIONS.get(
            role,
            set()
        )
    )


# =====================================================
# EMAIL VALIDATION
# =====================================================

def is_valid_email(email):
    pattern = (
        r"^[A-Za-z0-9._%+-]+@"
        r"[A-Za-z0-9.-]+\."
        r"[A-Za-z]{2,}$"
    )
    return (
        re.match(
            pattern,
            email
        )
        is not None
    )

# =====================================================
# PASSWORD VALIDATION
# =====================================================

def validate_password(password):
    if len(password) < 8:
        return (
            False,
            "Password must contain at least 8 characters."
        )
    if not any(
        char.isupper()
        for char in password
    ):
        return (
            False,
            "Password must contain at least one uppercase letter."
        )
    if not any(
        char.islower()
        for char in password
    ):
        return (
            False,
            "Password must contain at least one lowercase letter."
        )
    if not any(
        char.isdigit()
        for char in password
    ):
        return (
            False,
            "Password must contain at least one number."
        )
    return (
        True,
        "Valid password."
    )


# =====================================================
# CHANGE PASSWORD
# =====================================================

def change_password(identifier,current_password,new_password,confirm_password):
    """
    Allows both admin and normal users
    to securely change their own password.
    """
    # -------------------------------------------------
    # BASIC VALIDATION
    # -------------------------------------------------

    identifier = identifier.strip()

    if not identifier:
        return False, "Username or email is required."
    if not current_password:
        return False, "Current password is required."
    if not new_password:
        return False, "New password is required."
    if not confirm_password:
        return False, "Please confirm your new password."

    # -------------------------------------------------
    # CONFIRM PASSWORD
    # -------------------------------------------------

    if new_password != confirm_password:
        return (False,"New password and confirm password do not match.")

    # -------------------------------------------------
    # VALIDATE NEW PASSWORD
    # -------------------------------------------------

    valid,message = validate_password(new_password)
    if not valid:
        return False, message

    # -------------------------------------------------
    # GET USER
    # -------------------------------------------------

    user = get_user_security_data(identifier)
    if user is None:
        return (False,"Username/email or current password is incorrect.")

    # -------------------------------------------------
    # CHECK ACCOUNT STATUS
    # -------------------------------------------------

    if not user["is_active"]:
        return (False,"This account has been disabled.")

    # -------------------------------------------------
    # VERIFY CURRENT PASSWORD
    # -------------------------------------------------

    if not verify_password(
        current_password,
        user["password_hash"]
    ):
        return (False,"Username/email or current password is incorrect.")

    # -------------------------------------------------
    # PREVENT SAME PASSWORD
    # -------------------------------------------------

    if verify_password(new_password,user["password_hash"]):
        return (False,"New password must be different from your current password.")

    # -------------------------------------------------
    # HASH NEW PASSWORD
    # -------------------------------------------------

    new_password_hash = hash_password(new_password)

    # -------------------------------------------------
    # UPDATE DATABASE
    # -------------------------------------------------

    updated = update_user_password(
        user["id"],
        new_password_hash
    )
    if not updated:
        return (False,"Unable to update password. Please try again.")

    # -------------------------------------------------
    # AUDIT LOG
    # -------------------------------------------------

    add_audit_log(
        user["username"],
        "PASSWORD_CHANGED",
        "User successfully changed their password."
    )
    return (True,"Password changed successfully.")

# =====================================================
# SIGNUP
# =====================================================

def signup_user(username,email,password,confirm_password):
    username = username.strip()
    email = email.strip().lower()
    if not username:
        return (False,"Username is required.")
    if len(username) < 3:
        return (False,"Username must contain at least 3 characters.")
    if not is_valid_email(email):
        return (False,"Please enter a valid email address.")
    if password != confirm_password:
        return (False,"Passwords do not match.")
    valid, message = validate_password(password)
    if not valid:
        return (False,message)

    # ---------------------------------------------
    # ALWAYS CREATE NORMAL USER
    # ---------------------------------------------

    success, message = create_user(
        username=username,
        email=email,
        password=password,
        role="user"
    )
    if success:
        add_audit_log(
            username,
            "ACCOUNT_CREATED",
            "New user account created."
        )
    return (success,message)

# =====================================================
# LOGIN
# =====================================================

def login_user(identifier,password):
    identifier = identifier.strip()
    if not identifier:
        return None
    if not password:
        return None

    # ---------------------------------------------
    # DATABASE AUTHENTICATION
    # ---------------------------------------------

    user = db_authenticate_user(identifier,password)

    # ---------------------------------------------
    # LOGIN FAILED
    # ---------------------------------------------

    if user is None:
        return None

    # ---------------------------------------------
    # AUDIT LOG
    # ---------------------------------------------

    add_audit_log(
        user["username"],
        "LOGIN",
        "User logged into the system."
    )

    # ---------------------------------------------
    # RETURN USER DICTIONARY
    # ---------------------------------------------

    return user


# =====================================================
# LOGOUT
# =====================================================

def logout_user(username):
    if username:
        add_audit_log(
            username,
            "LOGOUT",
            "User logged out."
        )

def get_audit_logs(limit=200):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            username,
            action,
            details,
            created_at
        FROM audit_logs
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )
    logs = cursor.fetchall()
    conn.close()
    return logs

