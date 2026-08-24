import logging


def test_setup_logging_writes_to_rotating_file(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test.db"))
    root_logger = logging.getLogger()
    root_logger.handlers = []  # isolate from any handler a prior test left behind

    import logging_setup
    logging_setup.setup_logging()
    logging.getLogger("some.module").info("hello test")
    for handler in root_logger.handlers:
        handler.flush()

    log_file = tmp_path / "app.log"
    assert log_file.exists()
    assert "hello test" in log_file.read_text()


def test_setup_logging_is_idempotent(tmp_path, monkeypatch):
    # app.py calls this on every Streamlit rerun — it must never accumulate
    # duplicate handlers (which would duplicate every log line, and leak a
    # file descriptor per rerun).
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test2.db"))
    root_logger = logging.getLogger()
    root_logger.handlers = []

    import logging_setup
    logging_setup.setup_logging()
    logging_setup.setup_logging()
    logging_setup.setup_logging()

    assert len(root_logger.handlers) == 1
