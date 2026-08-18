import streamlit as st
from database import init_database, create_user

def create_initial_admin():
    """
    Creates the first admin account from Streamlit Secrets.
    Required secrets:
        ADMIN_USERNAME
        ADMIN_EMAIL
        ADMIN_PASSWORD
    """
    username = st.secrets.get("ADMIN_USERNAME", "")
    email = st.secrets.get("ADMIN_EMAIL", "")
    password = st.secrets.get("ADMIN_PASSWORD", "")

    if not username or not email or not password:
        return False, "Admin secrets are not configured."
    
    init_database()

    success, message = create_user(
        username=username,
        email=email,
        password=password,
        role="admin"
    )
    return success, message