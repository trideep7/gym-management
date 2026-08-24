import logging
import os
from logging.handlers import RotatingFileHandler

import db


def setup_logging():
    root_logger = logging.getLogger()
    if root_logger.handlers:
        # Streamlit re-executes the whole script on every user interaction —
        # without this guard, every rerun would add another handler, so each
        # log line would be duplicated once per rerun and a file descriptor
        # would leak every time.
        return

    log_dir = os.path.dirname(db.get_db_path())
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "app.log")

    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )

    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
