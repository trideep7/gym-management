import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import db as db_module


@pytest.fixture
def conn(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_gym.db")
    monkeypatch.setenv("GYM_PHOTOS_DIR", str(tmp_path / "photos"))
    connection = db_module.get_connection(db_path)
    db_module.init_db(connection)
    yield connection
    connection.close()
