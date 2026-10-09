import json

from nano import config, db, doctor


def _configure_doctor_paths(tmp_path, monkeypatch):
    data = tmp_path / "data"
    models = tmp_path / "models"
    skills = tmp_path / "skills"
    for path in (data, models, skills):
        path.mkdir()
    monkeypatch.setattr(config, "DATA_DIR", data)
    monkeypatch.setattr(config, "MODEL_DIR", models)
    monkeypatch.setattr(config, "SKILLS_DIR", skills)
    database = data / "nano.sqlite3"
    monkeypatch.setattr(config, "DB_PATH", database)
    monkeypatch.setattr(db, "DB_PATH", database)
    monkeypatch.setattr(config, "HOST", "127.0.0.1")
    monkeypatch.delenv("NANO_API_TOKEN", raising=False)
    return database


def test_doctor_reports_healthy_local_setup_without_mutating_settings(tmp_path, monkeypatch):
    database = _configure_doctor_paths(tmp_path, monkeypatch)
    db.init_db()
    monkeypatch.setattr(
        doctor, "runtime_status",
        lambda: {"binary": True, "reachable": True, "configured_url": "http://127.0.0.1:9379"},
    )
    from nano import voice
    monkeypatch.setattr(voice, "voice_status", lambda: {
        "stt": {"ready": False}, "tts": {"ready": False},
    })

    report = doctor.run_checks()

    assert report["read_only"] is True
    assert report["overall"] in {"ok", "warn"}
    assert next(item for item in report["checks"] if item["name"] == "database")["status"] == "ok"
    assert next(item for item in report["checks"] if item["name"] == "model endpoint")["status"] == "ok"
    assert database.is_file()
    assert not list((tmp_path / "data").glob(".nano-doctor-*"))
    assert json.loads(json.dumps(report))["summary"]["fail"] == 0


def test_doctor_flags_remote_binding_without_token(tmp_path, monkeypatch):
    _configure_doctor_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(config, "HOST", "0.0.0.0")
    monkeypatch.delenv("NANO_API_TOKEN", raising=False)
    monkeypatch.setattr(
        doctor, "runtime_status",
        lambda: {"binary": False, "reachable": False, "configured_url": "http://127.0.0.1:9379"},
    )

    report = doctor.run_checks()

    assert report["overall"] == "fail"
    security = next(item for item in report["checks"] if item["name"] == "API security")
    assert security["status"] == "fail"
    assert "NANO_API_TOKEN" in security["detail"]
