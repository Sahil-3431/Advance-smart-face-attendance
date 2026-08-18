import streamlit as st
from pathlib import Path

# =====================================================
# LOAD MAIN CSS
# =====================================================

def load_main_css():
    css_path = (
        Path(__file__).resolve().parent
        / "assets"
        / "style.css"
    )
    if css_path.exists():
        with open(
            css_path,
            "r",
            encoding="utf-8"
        ) as file:
            css = file.read()
        st.markdown(
            f"""
            <style>
            {css}
            </style>
            """,
            unsafe_allow_html=True
        )

# =====================================================
# THEME STATE
# =====================================================

def initialize_theme():
    if "theme" not in st.session_state:
        st.session_state["theme"] = "light"

# =====================================================
# THEME TOGGLE
# =====================================================

def theme_toggle():
    initialize_theme()
    current_theme = (st.session_state["theme"])
    if current_theme == "light":
        button_label = "🌙 Dark Mode"
    else:
        button_label = "☀️ Light Mode"
    if st.sidebar.button(
        button_label,
        use_container_width=True,
        key="theme_toggle"
    ):
        if current_theme == "light":
            st.session_state["theme"] = "dark"
        else:
            st.session_state["theme"] = "light"
        st.rerun()

# =====================================================
# APPLY THEME
# =====================================================

def apply_theme():
    initialize_theme()
    theme = (st.session_state["theme"])
    st.markdown(
        f"""
        <script>
        document.documentElement
            .setAttribute(
                'data-theme',
                '{theme}'
            );

        </script>
        """,
        unsafe_allow_html=True
    )