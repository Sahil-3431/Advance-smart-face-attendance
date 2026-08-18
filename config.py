from pathlib import Path

# ==============================
# PROJECT PATHS
# ==============================

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "attendance.db"
YUNET_MODEL = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
SFACE_MODEL = MODEL_DIR / "face_recognition_sface_2021dec.onnx"


# ==============================
# FACE SETTINGS
# ==============================

FACE_CONFIDENCE = 0.90

# SFace cosine similarity threshold
# Higher = stricter recognition
FACE_MATCH_THRESHOLD = 0.363


# ==============================
# APP SETTINGS
# ==============================

APP_TITLE = "Smart Face Recognition Attendance"
APP_ICON = "👤"
DEVELOPER_NAME = "Sahil Khan"

# ==============================
# AUTHENTICATION SETTINGS
# ==============================

MIN_PASSWORD_LENGTH = 8
DEFAULT_USER_ROLE = "user"
ADMIN_ROLE = "admin"
USER_ROLE = "user"
SESSION_TIMEOUT_MINUTES = 60

# ==============================
# UI SETTINGS
# ==============================

DEFAULT_THEME = "light"
PRIMARY_COLOR = "#4F46E5"
SECONDARY_COLOR = "#7C3AED"
APP_VERSION = "2.0.0"

