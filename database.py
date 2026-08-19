import os
import hashlib
import secrets
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import tuple_row
from dotenv import load_dotenv


# =====================================================
# ENVIRONMENT
# =====================================================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL .env file ya Streamlit Secrets mein nahi mila."
    )

IST = ZoneInfo("Asia/Kolkata")


# =====================================================
# CONNECTION
# =====================================================

def get_connection():
    return psycopg.connect(
        DATABASE_URL,
        row_factory=tuple_row
    )


# =====================================================
# CURRENT IST TIME
# =====================================================

def get_current_time():
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


# =====================================================
# PASSWORD HASHING
# =====================================================

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000
    ).hex()

    return f"{salt}${password_hash}"


# =====================================================
# VERIFY PASSWORD
# =====================================================

def verify_password(password, stored_password):
    try:
        salt, stored_hash = stored_password.split("$", 1)

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000
        ).hex()

        return secrets.compare_digest(
            password_hash,
            stored_hash
        )

    except (ValueError, AttributeError):
        return False


# =====================================================
# INITIALIZE DATABASE
# =====================================================

def init_database():
    """
    Tables are already created in Supabase.
    This function only verifies the connection.
    """

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")

        conn.commit()

    finally:
        conn.close()


# =====================================================
# USER MANAGEMENT
# =====================================================

def create_user(username, email, password, role="user"):

    username = username.strip()
    email = email.strip().lower()

    if not username or not email or not password:
        return False, "All fields are required."

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    if role not in ("admin", "user"):
        role = "user"

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # CHECK USERNAME
            cursor.execute("""
                SELECT id
                FROM users
                WHERE username = %s
            """, (username,))

            if cursor.fetchone():
                return False, "Username already exists."

            # CHECK EMAIL
            cursor.execute("""
                SELECT id
                FROM users
                WHERE email = %s
            """, (email,))

            if cursor.fetchone():
                return False, "Email already registered."

            # HASH PASSWORD
            password_hash = hash_password(password)

            # CREATE USER
            cursor.execute("""
                INSERT INTO users
                (
                    username,
                    email,
                    password_hash,
                    role,
                    is_active,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                username,
                email,
                password_hash,
                role,
                1,
                get_current_time()
            ))

        conn.commit()

        return True, "Account created successfully."

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =====================================================
# AUTHENTICATE USER
# =====================================================

def authenticate_user(identifier, password):

    identifier = identifier.strip()

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    username,
                    email,
                    password_hash,
                    role,
                    is_active
                FROM users
                WHERE username = %s
                OR email = %s
            """, (
                identifier,
                identifier.lower()
            ))

            user = cursor.fetchone()

            if user is None:
                return None

            (
                user_id,
                username,
                email,
                stored_password,
                role,
                is_active
            ) = user

            if not is_active:
                return None

            if not verify_password(
                password,
                stored_password
            ):
                return None

            cursor.execute("""
                UPDATE users
                SET last_login = %s
                WHERE id = %s
            """, (
                get_current_time(),
                user_id
            ))

        conn.commit()

        return {
            "id": user_id,
            "username": username,
            "email": email,
            "role": role
        }

    finally:
        conn.close()


# =====================================================
# GET USER BY ID
# =====================================================

def get_user_by_id(user_id):

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    username,
                    email,
                    role,
                    is_active,
                    created_at,
                    last_login
                FROM users
                WHERE id = %s
            """, (user_id,))

            user = cursor.fetchone()

            if user is None:
                return None

            return {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "role": user[3],
                "is_active": user[4],
                "created_at": user[5],
                "last_login": user[6]
            }

    finally:
        conn.close()


# =====================================================
# GET USER SECURITY DATA
# =====================================================

def get_user_security_data(identifier):

    identifier = identifier.strip()

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    username,
                    email,
                    password_hash,
                    role,
                    is_active
                FROM users
                WHERE username = %s
                OR email = %s
            """, (
                identifier,
                identifier.lower()
            ))

            user = cursor.fetchone()

            if user is None:
                return None

            return {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "password_hash": user[3],
                "role": user[4],
                "is_active": user[5]
            }

    finally:
        conn.close()


# =====================================================
# UPDATE USER PASSWORD
# =====================================================

def update_user_password(user_id, new_password_hash):

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                UPDATE users
                SET password_hash = %s
                WHERE id = %s
            """, (
                new_password_hash,
                user_id
            ))

            changed = cursor.rowcount > 0

        conn.commit()

        return changed

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =====================================================
# GET ALL USERS
# =====================================================

def get_users():

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    username,
                    email,
                    role,
                    is_active,
                    created_at,
                    last_login
                FROM users
                ORDER BY id DESC
            """)

            return cursor.fetchall()

    finally:
        conn.close()


# =====================================================
# CHANGE USER STATUS
# =====================================================

def set_user_status(user_id, is_active):

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                UPDATE users
                SET is_active = %s
                WHERE id = %s
            """, (
                1 if is_active else 0,
                user_id
            ))

            changed = cursor.rowcount > 0

        conn.commit()

        return changed

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =====================================================
# CHANGE USER ROLE
# =====================================================

def set_user_role(user_id, role):

    if role not in ("admin", "user"):
        return False

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                UPDATE users
                SET role = %s
                WHERE id = %s
            """, (
                role,
                user_id
            ))

            changed = cursor.rowcount > 0

        conn.commit()

        return changed

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =====================================================
# DELETE USER
# =====================================================

def delete_user(user_id):

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                DELETE FROM users
                WHERE id = %s
            """, (user_id,))

            deleted = cursor.rowcount > 0

        conn.commit()

        return deleted

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =====================================================
# AUDIT LOG
# =====================================================

def add_audit_log(username, action, details=""):

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                INSERT INTO audit_logs
                (
                    username,
                    action,
                    details,
                    created_at
                )
                VALUES (%s, %s, %s, %s)
            """, (
                username,
                action,
                details,
                get_current_time()
            ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =====================================================
# GET AUDIT LOGS
# =====================================================

def get_audit_logs(limit=100):

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT
                    username,
                    action,
                    details,
                    created_at
                FROM audit_logs
                ORDER BY id DESC
                LIMIT %s
            """, (limit,))

            return cursor.fetchall()

    finally:
        conn.close()


# =====================================================
# CHECK PERSON ID
# =====================================================

def person_exists(person_id):

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT id
                FROM people
                WHERE person_id = %s
            """, (person_id,))

            return cursor.fetchone() is not None

    finally:
        conn.close()


# =====================================================
# ADD PERSON
# =====================================================

def add_person(
    person_id,
    name,
    department,
    embedding
):

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                INSERT INTO people
                (
                    person_id,
                    name,
                    department,
                    embedding,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                person_id,
                name,
                department,
                embedding,
                get_current_time()
            ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =====================================================
# GET ALL PEOPLE
# =====================================================

def get_people():

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    person_id,
                    name,
                    department,
                    embedding,
                    created_at
                FROM people
                ORDER BY id DESC
            """)

            return cursor.fetchall()

    finally:
        conn.close()


# =====================================================
# CHECK TODAY ATTENDANCE
# =====================================================

def is_present_today(person_id):

    today = datetime.now(IST).strftime("%Y-%m-%d")

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT id
                FROM attendance
                WHERE person_id = %s
                AND date = %s
            """, (
                person_id,
                today
            ))

            return cursor.fetchone() is not None

    finally:
        conn.close()


# =====================================================
# MARK ATTENDANCE
# =====================================================

def mark_attendance(person_id, name):

    now = datetime.now(IST)

    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT id
                FROM attendance
                WHERE person_id = %s
                AND date = %s
            """, (
                person_id,
                today
            ))

            existing = cursor.fetchone()

            if existing is not None:
                return "EXISTING"

            cursor.execute("""
                INSERT INTO attendance
                (
                    person_id,
                    name,
                    date,
                    time,
                    status
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                person_id,
                name,
                today,
                current_time,
                "Present"
            ))

        conn.commit()

        return "NEW"

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =====================================================
# GET ATTENDANCE
# =====================================================

def get_attendance():

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT
                    person_id,
                    name,
                    date,
                    time,
                    status
                FROM attendance
                ORDER BY date DESC, time DESC
            """)

            return cursor.fetchall()

    finally:
        conn.close()


# =====================================================
# DELETE PERSON
# =====================================================

def delete_person(person_id):

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                DELETE FROM attendance
                WHERE person_id = %s
            """, (person_id,))

            cursor.execute("""
                DELETE FROM people
                WHERE person_id = %s
            """, (person_id,))

            deleted = cursor.rowcount

        conn.commit()

        return deleted > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =====================================================
# DELETE ONE ATTENDANCE
# =====================================================

def delete_attendance(person_id, date):

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                DELETE FROM attendance
                WHERE person_id = %s
                AND date = %s
            """, (
                person_id,
                date
            ))

            deleted = cursor.rowcount

        conn.commit()

        return deleted > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =====================================================
# DELETE ALL ATTENDANCE
# =====================================================

def clear_all_attendance():

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                DELETE FROM attendance
            """)

            deleted = cursor.rowcount

        conn.commit()

        return deleted

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =====================================================
# DATABASE MIGRATION
# =====================================================

def migrate_database():
    """
    Kept for compatibility with existing application code.
    Supabase schema is already created separately.
    """
    init_database()