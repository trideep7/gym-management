import logging
import time

import streamlit as st

logger = logging.getLogger(__name__)

DEFAULT_MESSAGE = "Something went wrong. Please try again."


def report_unexpected_error(friendly_message=DEFAULT_MESSAGE):
    ref_id = time.strftime("%H:%M:%S")
    logger.exception("Unexpected error (ref %s)", ref_id)
    st.error(
        f"{friendly_message} (Ref: {ref_id}) "
        "If this keeps happening, contact support with this reference."
    )


def safe_action(fn, friendly_message=DEFAULT_MESSAGE):
    try:
        return True, fn()
    except Exception:
        report_unexpected_error(friendly_message)
        return False, None
