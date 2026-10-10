import sqlite3

from nano import config, db, scheduler
from nano.supervisor import run_supervisor_cycle, supervisor_status


class AliveWorker:
    def is_alive(self):
        return True


def _setup_db(tmp_path, monkeypatch):
    path = tmp_path / "nano.sqlite3"
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(config, "DB_PATH", path)
    db.init_db()
    scheduler.init_scheduler_db()
    return path


def test_supervisor_reports_health_and_safe_boundaries(tmp_path, monkeypatch):
    _setup_db(tmp_path, monkeypatch)
    monkeypatch.setattr(scheduler, "_thread", AliveWorker())
    scheduler._stop.clear()
    monkeypatch.setattr("nano.runtime.status", lambda: {"reachable": True})
    report = run_supervisor_cycle(force=True)
    assert report["status"] == "ok"
    assert {check["name"] for check in report["checks"]} >= {
        "sqlite_integrity", "required_tables", "litert_lm", "scheduler_worker"
    }
    assert report["safety"]["database_auto_repair"] is False
    assert report["safety"]["source_code_changes"] is False
    state = supervisor_status()
    assert state["latest"]["status"] == "ok"


def test_supervisor_only_attempts_scheduler_recovery_when_enabled(tmp_path, monkeypatch):
    _setup_db(tmp_path, monkeypatch)
    monkeypatch.setattr(scheduler, "_thread", None)
    scheduler._stop.clear()
    monkeypatch.setattr("nano.runtime.status", lambda: {"reachable": False})
    attempts = []
    monkeypatch.setattr(scheduler, "start_scheduler", lambda: attempts.append("restart"))
    monkeypatch.setattr("nano.supervisor._last_scheduler_restart", None)
    from nano.settings import set_value
    set_value("auto_error_resolver_enabled", "true")
    report = run_supervisor_cycle(force=True)
    assert attempts == ["restart"]
    assert any(action["action"] == "restart_scheduler_thread" for action in report["actions"])
    assert report["safety"]["arbitrary_process_restart"] is False


def test_supervisor_reports_database_bootstrap_failure_without_crashing(tmp_path, monkeypatch):
    _setup_db(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "nano.supervisor._ensure_db",
        lambda: (_ for _ in ()).throw(sqlite3.DatabaseError("database disk image is malformed")),
    )

    report = run_supervisor_cycle(force=True)
    assert report["status"] == "error"
    assert report["manual_repair_required"] is True
    assert report["actions"] == []
    assert report["safety"]["database_auto_repair"] is False

    state = supervisor_status()
    assert state["latest"]["status"] == "error"
    assert "database_access_error" in state["latest"]
    assert state["events"] == []
