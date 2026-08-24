import os

import streamlit as st

INK = "#15171C"
EMBER = "#FF5A29"
SIDEBAR_TEXT = "#F5F5F5"

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
WORDMARK_LOGO = os.path.join(_ASSETS_DIR, "logo_wordmark.svg")
ICON_LOGO = os.path.join(_ASSETS_DIR, "logo_icon.svg")

_FONT_IMPORT_URL = (
    "https://fonts.googleapis.com/css2"
    "?family=Bebas+Neue&family=Inter:wght@400;500;600;700&display=swap"
)


def apply_theme():
    st.markdown(
        f"""
        <style>
        @import url('{_FONT_IMPORT_URL}');

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        h1, h2, h3 {{
            font-family: 'Bebas Neue', sans-serif;
            letter-spacing: 0.03em;
        }}

        [data-testid="stSidebar"] {{
            background-color: {INK};
        }}
        [data-testid="stSidebar"] * {{
            color: {SIDEBAR_TEXT} !important;
        }}
        [data-testid="stSidebar"] button {{
            background-color: transparent !important;
            border: 1px solid rgba(245, 245, 245, 0.35) !important;
        }}
        [data-testid="stSidebar"] button:hover {{
            border-color: {EMBER} !important;
            color: {EMBER} !important;
        }}

        .ft-logo-login {{
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            margin-bottom: 1.5rem;
        }}
        .ft-logo-login .ft-logo-mark {{
            font-size: 3.2rem;
        }}
        .ft-logo-login .ft-logo-text {{
            font-family: 'Bebas Neue', sans-serif;
            font-size: 2.6rem;
            letter-spacing: 0.08em;
            color: {INK};
            border-bottom: 4px solid {EMBER};
            padding-bottom: 0.3rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def set_sidebar_logo():
    st.logo(WORDMARK_LOGO, size="large", icon_image=ICON_LOGO)


def login_logo():
    st.markdown(
        '<div class="ft-logo-login">'
        '<span class="ft-logo-mark">🏋️</span>'
        '<span class="ft-logo-text">FITNESS TRIBE</span>'
        "</div>",
        unsafe_allow_html=True,
    )
