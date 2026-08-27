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


def page_bounds(total, page_size, page):
    """Clamp `page` into range and return (page, total_pages, start, end).

    Pulled out of the widget below so the arithmetic -- the ceiling
    division and the clamping that keeps a viewer from being stranded on
    a page that no longer exists after a delete -- is testable without a
    Streamlit runtime.
    """
    total_pages = max(1, -(-total // page_size))
    page = min(max(page, 1), total_pages)
    start = (page - 1) * page_size
    return page, total_pages, start, min(start + page_size, total)


def paginate(items, page_size, state_key):
    """Return (page_items, render_controls) for one paginated list.

    The controls are handed back as a callable rather than drawn here, so
    a caller can render rows first and place prev/next underneath them --
    which is where every list in this app already puts them.

    `state_key` names this list's page number in session_state, so two
    paginated lists on one screen don't fight over the same counter.
    """
    if state_key not in st.session_state:
        st.session_state[state_key] = 1
    page, total_pages, start, end = page_bounds(len(items), page_size, st.session_state[state_key])
    st.session_state[state_key] = page

    def render_controls():
        if total_pages <= 1:
            return
        col_prev, col_page, col_next = st.columns([1, 2, 1])
        if col_prev.button("← Previous", key=f"{state_key}_prev", disabled=page <= 1):
            st.session_state[state_key] -= 1
            st.rerun()
        col_page.write(f"Page {page} of {total_pages}")
        if col_next.button("Next →", key=f"{state_key}_next", disabled=page >= total_pages):
            st.session_state[state_key] += 1
            st.rerun()

    return items[start:end], render_controls
