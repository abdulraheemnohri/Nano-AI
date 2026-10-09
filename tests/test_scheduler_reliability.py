import pytest

from nano.db import init_db, rows, run
from nano.scheduler import (
    create_job,
    init_scheduler_db,
    list_jobs,
    list_runs,
    retry_job,
    run_job,
)


def setup_scheduler_db(tmp_path, monkeypatch):
    import nano.config as config
    import nano.db as db

    path = tmp_path / "scheduler.sqlite3"
    monkeypatch.setattr(config, "DB_PATH", path)
    monkeypatch.setattr(db, "DB_PATH", path)
    init_db()
    init_scheduler_db()
    return path


def test_scheduler_failure_schedules_bounded_exponential_retries(tmp_path, monkeypatch):
    setup_scheduler_db(tmp_path, monkeypatch)
    from nano import core

    monkeypatch.setattr(core, "respond", lambda *args: (_ for _ in ()).throw(RuntimeError("model unavailable")))
    job = create_job("Retry test", "assistant_prompt", {"prompt": "Check status"}, 3600, max_attempts=2, retry_delay_seconds=5)
    first = run_job(job)
    assert first["status"] == "retry_scheduled"
    current = list_jobs()[0]
    assert current["attempt_count"] == 1
    assert "model unavailable" in current["last_error"]
    assert list_runs(job["id"])[0]["status"] == "error"
    assert list_runs(job["id"])[0]["attempt"] == 1

    second = run_job(current)
    assert second["status"] == "failed"
    current = list_jobs()[0]
    assert current["attempt_count"] == 0
    assert current["last_error"]
    assert list_runs(job["id"])[0]["attempt"] == 2


def test_scheduler_success_clears_retry_state(tmp_path, monkeypatch):
    setup_scheduler_db(tmp_path, monkeypatch)
    from nano import core

    job = create_job("Success test", "assistant_prompt", {"prompt": "Run"}, 3600, max_attempts=3, retry_delay_seconds=5)
    run("UPDATE scheduled_jobs SET attempt_count=1,last_error='previous error' WHERE id=?", (job["id"],))
    monkeypatch.setattr(core, "respond", lambda *args: "Task completed.")
    current = list_jobs()[0]
    result = run_job(current)
    assert result["status"] == "complete"
    updated = list_jobs()[0]
    assert updated["attempt_count"] == 0
    assert updated["last_error"] is None
    assert list_runs(job["id"])[0]["result"] == "Task completed."


def test_scheduler_startup_recovers_interrupted_run(tmp_path, monkeypatch):
    setup_scheduler_db(tmp_path, monkeypatch)
    from nano.scheduler import _recover_interrupted_runs

    job = create_job("Crash recovery", "assistant_prompt", {"prompt": "Run"}, 3600, max_attempts=3, retry_delay_seconds=5)
    run("UPDATE scheduled_jobs SET claimed_at=CURRENT_TIMESTAMP,next_run_at='2099-01-01T00:00:00+00:00' WHERE id=?", (job["id"],))
    run("INSERT INTO scheduled_runs(job_id,status,result,attempt) VALUES(?,?,?,?)", (job["id"], "running", "", 1))

    _recover_interrupted_runs()

    recovered = list_jobs()[0]
    history = list_runs(job["id"])[0]
    assert history["status"] == "interrupted"
    assert recovered["claimed_at"] is None
    assert recovered["attempt_count"] == 1
    assert recovered["last_error"] and "interrupted" in recovered["last_error"]


def test_manual_retry_reenables_job_and_clears_error(tmp_path, monkeypatch):
    setup_scheduler_db(tmp_path, monkeypatch)
    job = create_job("Manual retry", "assistant_prompt", {"prompt": "Run"}, 3600)
    run("UPDATE scheduled_jobs SET enabled=0,attempt_count=2,last_error='failed' WHERE id=?", (job["id"],))

    retried = retry_job(job["id"])
    assert retried["enabled"] == 1
    assert retried["attempt_count"] == 0
    assert retried["last_error"] is None
    assert retried["claimed_at"] is None
    assert retried["next_run_at"]
    with pytest.raises(KeyError):
        retry_job(99999)


def test_manual_retry_refuses_to_duplicate_an_active_run(tmp_path, monkeypatch):
    setup_scheduler_db(tmp_path, monkeypatch)
    job = create_job("Already running", "assistant_prompt", {"prompt": "Run"}, 3600)
    run("UPDATE scheduled_jobs SET claimed_at=CURRENT_TIMESTAMP WHERE id=?", (job["id"],))
    run("INSERT INTO scheduled_runs(job_id,status,result,attempt) VALUES(?,?,?,?)", (job["id"], "running", "", 1))

    with pytest.raises(ValueError, match="already running"):
        retry_job(job["id"])


def test_job_timeout_records_error_and_schedules_retry(tmp_path, monkeypatch):
    setup_scheduler_db(tmp_path, monkeypatch)
    import time as _time
    from nano import core

    def slow_respond(*args):
        _time.sleep(7)
        return "too late"

    monkeypatch.setattr(core, "respond", slow_respond)
    job = create_job("Timeout test", "assistant_prompt", {"prompt": "Run"}, 3600, max_attempts=2, retry_delay_seconds=5, timeout_seconds=5)
    result = run_job(job)
    assert result["status"] == "retry_scheduled"
    assert "timed out after 5 seconds" in result["error"]
    current = list_jobs()[0]
    assert current["attempt_count"] == 1
    assert "JobTimeoutError" in current["last_error"]
    assert list_runs(job["id"])[0]["status"] == "error"


def test_job_timeout_validation_and_default(tmp_path, monkeypatch):
    setup_scheduler_db(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="timeout_seconds"):
        create_job("Bad timeout", "assistant_prompt", {"prompt": "Run"}, 3600, timeout_seconds=2)
    job = create_job("Default timeout", "assistant_prompt", {"prompt": "Run"}, 3600)
    assert job["timeout_seconds"] == 300
