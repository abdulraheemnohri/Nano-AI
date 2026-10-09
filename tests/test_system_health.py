from nano import config, db, scheduler, system_health


def _setup_health_db(tmp_path, monkeypatch):
    path = tmp_path / "health.sqlite3"
    monkeypatch.setattr(config, "DB_PATH", path)
    monkeypatch.setattr(db, "DB_PATH", path)
    db.init_db()
    scheduler.init_scheduler_db()
    monkeypatch.setattr(
        system_health, "runtime_status",
        lambda: {
            "reachable": True, "binary": True,
            "configured_url": "http://127.0.0.1:9379",
            "model": "test-model", "models": ["test-model"],
        },
    )
    monkeypatch.setattr(system_health, "voice_status", lambda: {
        "stt": {"ready": False}, "tts": {"ready": False},
    })
    monkeypatch.setattr(scheduler, "_thread", None)
    return path


def test_system_health_returns_read_only_live_counts_and_task_errors(tmp_path, monkeypatch):
    _setup_health_db(tmp_path, monkeypatch)
    conversation_id = db.run("INSERT INTO conversations(title) VALUES(?)", ("Health test",))
    db.run("INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)", (conversation_id, "user", "hello"))
    db.run("INSERT INTO memories(kind,content,status) VALUES(?,?,?)", ("fact", "local memory", "active"))
    job_id = scheduler.create_job("Health task", "assistant_prompt", {"prompt": "check"}, 3600)["id"]
    db.run(
        "INSERT INTO scheduled_runs(job_id,status,result,attempt) VALUES(?,?,?,?)",
        (job_id, "error", "RuntimeError: test failure", 2),
    )

    report = system_health.system_health()

    assert report["read_only"] is True
    assert report["overall"] == "warn"
    checks = {item["name"]: item for item in report["checks"]}
    assert checks["database"]["status"] == "ok"
    assert checks["database"]["counts"]["messages"] == 1
    assert checks["database"]["counts"]["active_memories"] == 1
    assert checks["model"]["status"] == "ok"
    assert checks["model"]["model_loaded"] is True
    assert checks["background_tasks"]["jobs_total"] == 1
    assert checks["background_tasks"]["recent_errors"][0]["error"] == "RuntimeError: test failure"


def test_system_health_does_not_treat_optional_voice_as_a_failure(tmp_path, monkeypatch):
    _setup_health_db(tmp_path, monkeypatch)
    class RunningThread:
        def is_alive(self):
            return True
    class ClearStopEvent:
        def is_set(self):
            return False
    monkeypatch.setattr(scheduler, "_thread", RunningThread())
    monkeypatch.setattr(scheduler, "_stop", ClearStopEvent())
    report = system_health.system_health()
    assert report["overall"] == "ok"
    voice = next(item for item in report["checks"] if item["name"] == "voice")
    assert voice["status"] == "info"


def test_system_health_warns_when_endpoint_has_no_served_model(tmp_path, monkeypatch):
    _setup_health_db(tmp_path, monkeypatch)
    monkeypatch.setattr(
        system_health, "runtime_status",
        lambda: {
            "reachable": True, "binary": True,
            "configured_url": "http://127.0.0.1:9379",
            "model": "test-model", "models": ["unrelated-model"],
        },
    )

    report = system_health.system_health()

    model = next(item for item in report["checks"] if item["name"] == "model")
    assert model["status"] == "warn"
    assert model["model_loaded"] is False
    assert "nano-ai download-model" in model["detail"]
    assert report["read_only"] is True
