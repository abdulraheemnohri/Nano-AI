import json

import pytest

from nano.db import init_db, run
from nano.learning import feedback_examples, feedback_summary, save_response_feedback


def configure_db(tmp_path, monkeypatch):
    import nano.config as config
    import nano.db as db
    path = tmp_path / "feedback.sqlite3"
    monkeypatch.setattr(config, "DB_PATH", path)
    monkeypatch.setattr(db, "DB_PATH", path)
    init_db()
    cid = run("INSERT INTO conversations(title) VALUES(?)", ("Feedback test",))
    return cid


def test_feedback_is_saved_and_available_as_future_guidance(tmp_path, monkeypatch):
    cid = configure_db(tmp_path, monkeypatch)
    result = save_response_feedback(cid, "Explain simply", "A complicated answer", -1, "Use shorter sentences and one example.")
    assert result["correction_saved"] is True
    assert feedback_examples(5) == [{"rating": -1, "correction": "Use shorter sentences and one example."}]
    assert feedback_summary() == {"total": 1, "helpful": 0, "unhelpful": 1, "corrections": 1}


def test_feedback_rejects_invalid_rating_and_overlong_correction(tmp_path, monkeypatch):
    cid = configure_db(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        save_response_feedback(cid, "question", "answer", 0)
    with pytest.raises(ValueError):
        save_response_feedback(cid, "question", "answer", 1, "x" * 2001)


def test_proactive_talk_is_local_and_audited(tmp_path, monkeypatch):
    cid = configure_db(tmp_path, monkeypatch)
    import nano.model as model
    from nano.core import generate_proactive_talk
    monkeypatch.setattr(model, "chat", lambda history, prompt, context: "A short local check-in.")
    assert generate_proactive_talk("Ask if I need help.") == "A short local check-in."
    from nano.db import rows
    event = rows("SELECT event_type,result FROM learning_events ORDER BY id DESC LIMIT 1")[0]
    assert event["event_type"] == "autonomous_talk"
    assert event["result"] == "A short local check-in."


def test_update_check_compares_remote_commit_without_mutating_checkout(monkeypatch):
    import nano.updates as updates
    monkeypatch.setattr(updates, "_checkout", lambda: {
        "branch": "main", "local_sha": "a" * 40, "dirty": False,
        "origin": "https://github.com/abdulraheemnohri/Nano-AI.git",
    })

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, limit):
            return json.dumps({"sha": "b" * 40, "html_url": "https://github.com/abdulraheemnohri/Nano-AI/commit/" + "b" * 40}).encode()

    monkeypatch.setattr(updates.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    result = updates.check_update()
    assert result["update_available"] is True
    assert result["can_apply"] is True
    assert result["latest_sha"] == "b" * 40


def test_update_apply_requires_explicit_approval():
    from nano.updates import apply_update
    with pytest.raises(PermissionError):
        apply_update(False)


def test_feedback_api_and_autonomous_talk_opt_in(tmp_path, monkeypatch):
    import nano.config as config
    import nano.db as db
    import nano.app as app_module
    from nano.settings import set_value
    from fastapi.testclient import TestClient

    path = tmp_path / "api.sqlite3"
    monkeypatch.setattr(config, "DB_PATH", path)
    monkeypatch.setattr(db, "DB_PATH", path)
    init_db()
    set_value("autonomous_talk_enabled", "false")
    with TestClient(app_module.app) as client:
        conversation = client.post("/api/conversations", json={"title": "Feedback API"}).json()
        feedback = client.post("/api/feedback", json={
            "conversation_id": conversation["id"],
            "user_text": "Explain this",
            "assistant_text": "Here is an answer",
            "rating": 1,
            "correction": "Prefer bullet points",
        })
        assert feedback.status_code == 200
        assert client.get("/api/learning/feedback-summary").json()["helpful"] == 1
        assert client.post("/api/talk/proactive", json={}).status_code == 403

        set_value("autonomous_talk_enabled", "true")
        set_value("voice_enabled", "true")
        set_value("auto_tts", "true")
        monkeypatch.setattr(app_module, "generate_proactive_talk", lambda prompt: "A local check-in.")
        result = client.post("/api/talk/proactive", json={})
        assert result.status_code == 200
        assert result.json()["answer"] == "A local check-in."


def test_pre_update_database_snapshot_is_integrity_checked(tmp_path, monkeypatch):
    import sqlite3
    import nano.config as config
    import nano.updates as updates

    db_path = tmp_path / "nano.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE sample(value TEXT)")
        connection.execute("INSERT INTO sample VALUES('preserve me')")
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    snapshot = updates._snapshot_database()
    assert snapshot is not None
    with sqlite3.connect(snapshot) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT value FROM sample").fetchone()[0] == "preserve me"


def test_rollback_requires_explicit_approval():
    from nano.updates import rollback_update
    with pytest.raises(PermissionError):
        rollback_update(False)


def test_rollback_refuses_to_reset_if_head_moved(tmp_path, monkeypatch):
    import json
    import nano.config as config
    import nano.updates as updates

    root = tmp_path / "data"
    recovery = root / "update-recovery"
    recovery.mkdir(parents=True)
    (recovery / "latest-update.json").write_text(json.dumps({
        "previous_sha": "a" * 40,
        "current_sha": "b" * 40,
        "database_snapshot": None,
    }))
    monkeypatch.setattr(config, "DATA_DIR", root)
    monkeypatch.setattr(updates, "_checkout", lambda: {
        "branch": "main", "local_sha": "c" * 40, "dirty": False,
        "origin": "https://github.com/abdulraheemnohri/Nano-AI.git",
    })
    with pytest.raises(RuntimeError, match="HEAD differs"):
        updates.rollback_update(True)



def test_quality_report_counts_feedback_and_reports_descriptive_rates(tmp_path, monkeypatch):
    from nano.learning import quality_report

    cid = configure_db(tmp_path, monkeypatch)
    save_response_feedback(cid, "Q1", "A1", 1)
    save_response_feedback(cid, "Q2", "A2", -1, "Add a concrete example.")
    save_response_feedback(cid, "Q3", "A3", 1)

    report = quality_report()
    assert report["total"] == 3
    assert report["helpful"] == 2
    assert report["unhelpful"] == 1
    assert report["corrections"] == 1
    assert report["helpful_rate_percent"] == 66.7
    assert report["correction_rate_percent"] == 33.3
    assert report["last_7_days"] == 3
    assert report["last_7_days_helpful_rate_percent"] == 66.7
    assert report["daily"] and sum(day["total"] for day in report["daily"]) == 3


def test_quality_report_handles_no_feedback_without_division_by_zero(tmp_path, monkeypatch):
    configure_db(tmp_path, monkeypatch)
    from nano.learning import quality_report

    report = quality_report()
    assert report["total"] == 0
    assert report["helpful_rate_percent"] is None
    assert report["correction_rate_percent"] is None
    assert report["helpful_rate_change_percentage_points"] is None
    assert report["daily"] == []
