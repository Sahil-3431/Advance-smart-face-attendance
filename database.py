import sqlite3
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


# =====================================================
# DATABASE PATH
# =====================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)
DATABASE_PATH = DATA_DIR / "attendance.db"
IST = ZoneInfo("Asia/Kolkata")

# =====================================================
# CONNECTION
# =====================================================

def get_connection():
    conn = sqlite3.connect(
        str(DATABASE_PATH),
        check_same_thread=False
    )
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

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
        return secrets.compare_digest(password_hash,stored_hash)
    except (ValueError, AttributeError):
        return False


# =====================================================
# INITIALIZE DATABASE
# =====================================================

def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    # =================================================
    # USERS TABLE
    # =================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            last_login TEXT
        )
    """)

    # =================================================
    # PEOPLE TABLE
    # =================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT,
            embedding BLOB NOT NULL,
            created_at TEXT
        )
    """)

    # =================================================
    # ATTENDANCE TABLE
    # =================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    # =================================================
    # AUDIT LOGS
    # =================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL

        )
    """)

    # =================================================
    # APP SETTINGS
    # =================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT

        )
    """)
    conn.commit()
    conn.close()


# =====================================================
# USER MANAGEMENT
# =====================================================

def create_user(username,email,password,role="user"):
    username = username.strip()
    email = email.strip().lower()
    if not username or not email or not password:
        return False, "All fields are required."
    if len(password) < 8:
        return False, "Password must contain at least 8 characters."
    if role not in ("admin", "user"):
        role = "user"
    conn = get_connection()
    cursor = conn.cursor()

    # ---------------------------------------------
    # CHECK USERNAME
    # ---------------------------------------------

    cursor.execute("""
        SELECT id
        FROM users
        WHERE username = ?
    """, (username,))
    if cursor.fetchone():
        conn.close()
        return False, "Username already exists."

    # ---------------------------------------------
    # CHECK EMAIL
    # ---------------------------------------------

    cursor.execute("""
        SELECT id
        FROM users
        WHERE email = ?
    """, (email,))
    if cursor.fetchone():
        conn.close()
        return False, "Email already registered."

    # ---------------------------------------------
    # HASH PASSWORD
    # ---------------------------------------------

    password_hash = hash_password(password)

    # ---------------------------------------------
    # CREATE USER
    # ---------------------------------------------

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
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        username,
        email,
        password_hash,
        role,
        1,
        get_current_time()
    ))
    conn.commit()
    conn.close()
    return True, "Account created successfully."


# =====================================================
# AUTHENTICATE USER
# =====================================================

def authenticate_user(identifier, password):
    identifier = identifier.strip()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            id,
            username,
            email,
            password_hash,
            role,
            is_active
        FROM users
        WHERE username = ?
        OR email = ?
    """, (
        identifier,
        identifier.lower()
    ))
    user = cursor.fetchone()
    if user is None:
        conn.close()
        return None

    (
        user_id,
        username,
        email,
        stored_password,
        role,
        is_active
    ) = user

    # ---------------------------------------------
    # ACCOUNT DISABLED
    # ---------------------------------------------

    if not is_active:
        conn.close()
        return None

    # ---------------------------------------------
    # VERIFY PASSWORD
    # ---------------------------------------------

    if not verify_password(password,stored_password):
        conn.close()
        return None

    # ---------------------------------------------
    # UPDATE LAST LOGIN
    # ---------------------------------------------

    cursor.execute("""
        UPDATE users
        SET last_login = ?
        WHERE id = ?
    """, (
        get_current_time(),
        user_id
    ))
    conn.commit()
    conn.close()
    return {
        "id": user_id,
        "username": username,
        "email": email,
        "role": role
    }

# =====================================================
# GET USER BY ID
# =====================================================

def get_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()
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
        WHERE id = ?
    """, (user_id,))
    user = cursor.fetchone()
    conn.close()
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


# =====================================================
# GET USER SECURITY DATA
# =====================================================

def get_user_security_data(identifier):
    """
    Get user authentication data using username or email.
    Password hash is returned only for password verification.
    """
    identifier = identifier.strip()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            id,
            username,
            email,
            password_hash,
            role,
            is_active
        FROM users
        WHERE username = ?
        OR email = ?
        """,
        (
            identifier,
            identifier.lower()
        )
    )
    user = cursor.fetchone()
    conn.close()
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

# =====================================================
# UPDATE USER PASSWORD
# =====================================================

def update_user_password(user_id, new_password_hash):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE users
        SET password_hash = ?
        WHERE id = ?
        """,
        (
            new_password_hash,
            user_id
        )
    )
    changed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return changed

# =====================================================
# GET ALL USERS
# =====================================================

def get_users():
    conn = get_connection()
    cursor = conn.cursor()
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
    users = cursor.fetchall()
    conn.close()
    return users

# =====================================================
# CHANGE USER STATUS
# =====================================================

def set_user_status(user_id, is_active):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET is_active = ?
        WHERE id = ?
    """, (
        1 if is_active else 0,
        user_id
    ))
    changed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return changed

# =====================================================
# CHANGE USER ROLE
# =====================================================

def set_user_role(user_id, role):
    if role not in ("admin", "user"):
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET role = ?
        WHERE id = ?
    """, (
        role,
        user_id
    ))
    changed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return changed

# =====================================================
# DELETE USER
# =====================================================

def delete_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM users
        WHERE id = ?
    """, (user_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

# =====================================================
# AUDIT LOG
# =====================================================

def add_audit_log(username,action,details=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_logs
        (
            username,
            action,
            details,
            created_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        username,
        action,
        details,
        get_current_time()
    ))
    conn.commit()
    conn.close()

# =====================================================
# GET AUDIT LOGS
# =====================================================

def get_audit_logs(limit=100):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            username,
            action,
            details,
            created_at
        FROM audit_logs
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    logs = cursor.fetchall()
    conn.close()
    return logs

# =====================================================
# CHECK PERSON ID
# =====================================================

def person_exists(person_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id
        FROM people
        WHERE person_id = ?
    """, (person_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# =====================================================
# ADD PERSON
# =====================================================

def add_person(person_id,name,department,embedding):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO people
        (
            person_id,
            name,
            department,
            embedding,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        person_id,
        name,
        department,
        embedding,
        get_current_time()
    ))
    conn.commit()
    conn.close()

# =====================================================
# GET ALL PEOPLE
# =====================================================

def get_people():
    conn = get_connection()
    cursor = conn.cursor()
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
    rows = cursor.fetchall()
    conn.close()
    return rows

# =====================================================
# CHECK TODAY ATTENDANCE
# =====================================================

def is_present_today(person_id):
    today = datetime.now(IST).strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id
        FROM attendance
        WHERE person_id = ?
        AND date = ?
    """, (
        person_id,
        today
    ))
    result = cursor.fetchone()
    conn.close()
    return result is not None


# =====================================================
# MARK ATTENDANCE
# =====================================================

def mark_attendance(person_id,name):
    now = datetime.now(IST)
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    conn = get_connection()
    cursor = conn.cursor()

    # ---------------------------------------------
    # CHECK EXISTING ATTENDANCE
    # ---------------------------------------------

    cursor.execute("""
        SELECT id
        FROM attendance
        WHERE person_id = ?
        AND date = ?
    """, (
        person_id,
        today
    ))
    existing = cursor.fetchone()

    # ---------------------------------------------
    # ALREADY PRESENT
    # ---------------------------------------------

    if existing is not None:
        conn.close()
        return "EXISTING"

    # ---------------------------------------------
    # NEW ATTENDANCE
    # ---------------------------------------------

    cursor.execute("""
        INSERT INTO attendance
        (
            person_id,
            name,
            date,
            time,
            status
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        person_id,
        name,
        today,
        current_time,
        "Present"
    ))
    conn.commit()
    conn.close()
    return "NEW"

# =====================================================
# GET ATTENDANCE
# =====================================================

def get_attendance():
    conn = get_connection()
    cursor = conn.cursor()
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
    rows = cursor.fetchall()
    conn.close()
    return rows

# =====================================================
# DELETE PERSON
# =====================================================

def delete_person(person_id):
    conn = get_connection()
    cursor = conn.cursor()

    # ---------------------------------------------
    # DELETE ATTENDANCE
    # ---------------------------------------------

    cursor.execute("""
        DELETE FROM attendance
        WHERE person_id = ?
    """, (person_id,))

    # ---------------------------------------------
    # DELETE PERSON
    # ---------------------------------------------

    cursor.execute("""
        DELETE FROM people
        WHERE person_id = ?
    """, (person_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted > 0

# =====================================================
# DELETE ONE ATTENDANCE
# =====================================================

def delete_attendance(person_id,date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM attendance
        WHERE person_id = ?
        AND date = ?
    """, (
        person_id,
        date
    ))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted > 0

# =====================================================
# DELETE ALL ATTENDANCE
# =====================================================

def clear_all_attendance():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""DELETE FROM attendance""")
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted

# =====================================================
# DATABASE MIGRATION
# =====================================================

def migrate_database():
    conn = get_connection()
    cursor = conn.cursor()

    # ---------------------------------------------
    # USERS TABLE
    # ---------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            last_login TEXT
        )
    """)

    # ---------------------------------------------
    # AUDIT LOGS
    # ---------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # ---------------------------------------------
    # APP SETTINGS
    # ---------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()