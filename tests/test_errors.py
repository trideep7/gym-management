import logging


def test_safe_action_returns_ok_and_value_on_success():
    from utils.errors import safe_action
    ok, value = safe_action(lambda: 42)
    assert ok is True
    assert value == 42


def test_safe_action_returns_false_and_none_on_exception():
    from utils.errors import safe_action

    def boom():
        raise RuntimeError("kaboom")

    ok, value = safe_action(boom)
    assert ok is False
    assert value is None


def test_safe_action_logs_the_exception(caplog):
    from utils.errors import safe_action

    def boom():
        raise RuntimeError("kaboom")

    with caplog.at_level(logging.ERROR):
        safe_action(boom)

    assert any(record.exc_info is not None for record in caplog.records)


def test_safe_action_success_path_does_not_return_none_as_failure_signal():
    # a wrapped function that legitimately returns None on success must not
    # be mistaken for a failure by callers checking the `ok` flag
    from utils.errors import safe_action
    ok, value = safe_action(lambda: None)
    assert ok is True
    assert value is None
