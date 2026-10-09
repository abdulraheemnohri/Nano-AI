import sqlite3

import pytest
from fastapi import HTTPException

import nano.app as app_module


def test_backup_creates_valid_sqlite_snapshot(tmp_path, monkeypatch):
    database = tmp_path / "nano.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE sample (value TEXT NOT NULL)")
    connection.execute("INSERT INTO sample(value) VALUES ('backup works')")
    connection.commit()
    connection.close()
    monkeypatch.setattr(app_module.config, "DB_PATH", database)

    response = app_module.backup_database()
    try:
        assert response.filename == "nano-ai-backup.sqlite3"
        snapshot = sqlite3.connect(response.path)
        try:
            assert snapshot.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert snapshot.execute("SELECT value FROM sample").fetchone()[0] == "backup works"
        finally:
            snapshot.close()
    finally:
        __import__("pathlib").Path(response.path).unlink(missing_ok=True)


def test_backup_returns_404_when_database_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module.config, "DB_PATH", tmp_path / "missing.sqlite3")
    with pytest.raises(HTTPException) as error:
        app_module.backup_database()
    assert error.value.status_code == 404
