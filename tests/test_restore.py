import asyncio
import io
import sqlite3

import pytest
from fastapi import HTTPException, UploadFile

import nano.app as app_module


def test_restore_rejects_invalid_sqlite_upload(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module.config, "DB_PATH", tmp_path / "nano.sqlite3")
    upload = UploadFile(filename="broken.sqlite3", file=io.BytesIO(b"not sqlite"))
    with pytest.raises(HTTPException) as error:
        asyncio.run(app_module.restore_database(upload))
    assert error.value.status_code == 400


def test_restore_keeps_a_recovery_snapshot(tmp_path, monkeypatch):
    current = tmp_path / "current.sqlite3"
    conn = sqlite3.connect(current)
    conn.execute("CREATE TABLE before_restore(value TEXT)")
    conn.execute("INSERT INTO before_restore VALUES ('old data')")
    conn.commit()
    conn.close()

    candidate = tmp_path / "candidate.sqlite3"
    conn = sqlite3.connect(candidate)
    conn.executescript(
        "CREATE TABLE conversations(id INTEGER PRIMARY KEY, title TEXT);"
        "CREATE TABLE messages(id INTEGER PRIMARY KEY, conversation_id INTEGER, role TEXT, content TEXT);"
        "CREATE TABLE memories(id INTEGER PRIMARY KEY, content TEXT);"
        "CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);"
        "CREATE TABLE skills(id INTEGER PRIMARY KEY, name TEXT);"
        "CREATE TABLE restored(value TEXT);"
        "INSERT INTO restored VALUES ('new data');"
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(app_module.config, "DB_PATH", current)
    upload = UploadFile(filename="backup.sqlite3", file=io.BytesIO(candidate.read_bytes()))
    result = asyncio.run(app_module.restore_database(upload))
    assert result["ok"] is True
    recovery = sqlite3.connect(tmp_path / "recovery" / result["recovery_backup"])
    try:
        assert recovery.execute("SELECT value FROM before_restore").fetchone()[0] == "old data"
    finally:
        recovery.close()
    restored = sqlite3.connect(current)
    try:
        assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert restored.execute("SELECT value FROM restored").fetchone()[0] == "new data"
    finally:
        restored.close()
