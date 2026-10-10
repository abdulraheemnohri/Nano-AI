"""Background health supervisor with bounded, auditable recovery actions."""
import json
import sqlite3
import threading
import time
from datetime import datetime, timezone

from . import config, scheduler
from .db import connect
from .settings import bool_value, int_value

_lock = threading.RLock()
_thread = None
_stop = threading.Event()
_last_cycle = None
_last_report = {"status": "not_run", "checks": [], "actions": []}
_MIN_RESTART_INTERVAL = 300
_last_scheduler_restart = None


def _ensure_db():
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS supervisor_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          severity TEXT NOT NULL,
          category TEXT NOT NULL,
          summary TEXT NOT NULL,
          details TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_supervisor_events_created ON supervisor_events(id DESC);
        """)


def _event(severity, category, summary, details=None):
    """Persist an event when possible; logging must never hide the health failure."""
    try:
        _ensure_db()
        with connect() as conn:
            conn.execute(
                "INSERT INTO supervisor_events(severity,category,summary,details) VALUES(?,?,?,?)",
                (severity, category, str(summary)[:500], json.dumps(details or {}, ensure_ascii=False)[:4000]),
            )
        return True
    except Exception:
        # The current health report remains the diagnostic source if SQLite is unavailable.
        return False


def run_supervisor_cycle(force=False):
    """Inspect health and apply only bounded recovery to Nano-owned worker threads."""
    global _last_cycle, _last_report, _last_scheduler_restart
    checks, actions = [], []
    try:
        _ensure_db()
    except Exception as exc:
        # A broken database must not prevent the supervisor from reporting the failure.
        report = {
            "status": "error",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "checks": [
                {"name": "sqlite_integrity", "status": "error", "detail": type(exc).__name__ + ": " + str(exc)[:300]},
                {"name": "required_tables", "status": "error", "detail": "Database unavailable; table checks could not run."},
            ],
            "actions": [],
            "safety": {"database_auto_repair": False, "arbitrary_process_restart": False, "source_code_changes": False, "approval_bypass": False},
            "manual_repair_required": True,
        }
        with _lock:
            _last_cycle = time.time()
            _last_report = report
        return report
    if not force and not bool_value("background_self_check_enabled", True):
        return {"status": "disabled", "checks": [], "actions": [], "checked_at": None}
    try:
        with sqlite3.connect(str(config.DB_PATH), timeout=3) as conn:
            conn.row_factory = sqlite3.Row
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        checks.append({"name": "sqlite_integrity", "status": "ok" if integrity == "ok" else "error", "detail": str(integrity)})
        required = {"settings", "conversations", "messages", "scheduled_jobs", "scheduled_runs"}
        missing = sorted(required - tables)
        checks.append({"name": "required_tables", "status": "ok" if not missing else "error", "missing": missing})
        if integrity != "ok" or missing:
            _event("error", "database", "Database integrity or required-table check needs manual repair.", {"integrity": integrity, "missing_tables": missing})
    except Exception as exc:
        checks.append({"name": "sqlite_integrity", "status": "error", "detail": type(exc).__name__ + ": " + str(exc)[:300]})
        _event("error", "database", "Database health check failed; no automatic database edits were attempted.", {"error": str(exc)[:500]})

    try:
        from .runtime import status as runtime_status
        runtime = runtime_status()
        reachable = bool(runtime.get("reachable"))
        checks.append({"name": "litert_lm", "status": "ok" if reachable else "warning", "reachable": reachable})
        if not reachable:
            _event("warning", "runtime", "LiteRT-LM endpoint is not reachable; check model service and configured URL.", {"url": config.LITERT_URL})
    except Exception as exc:
        checks.append({"name": "litert_lm", "status": "warning", "detail": type(exc).__name__ + ": " + str(exc)[:300]})
        _event("warning", "runtime", "Runtime diagnostics failed.", {"error": str(exc)[:500]})

    try:
        worker = getattr(scheduler, "_thread", None)
        alive = bool(worker and worker.is_alive() and not scheduler._stop.is_set())
        checks.append({"name": "scheduler_worker", "status": "ok" if alive else "warning", "alive": alive})
        if not alive and bool_value("auto_error_resolver_enabled", True):
            now = time.monotonic()
            if _last_scheduler_restart is None or now - _last_scheduler_restart >= _MIN_RESTART_INTERVAL:
                scheduler.start_scheduler()
                _last_scheduler_restart = now
                actions.append({"action": "restart_scheduler_thread", "status": "attempted", "scope": "Nano-owned worker only"})
                _event("recovery", "scheduler", "Attempted bounded restart of Nano's scheduler worker.")
            else:
                actions.append({"action": "restart_scheduler_thread", "status": "rate_limited"})
        elif not alive:
            actions.append({"action": "restart_scheduler_thread", "status": "disabled"})
    except Exception as exc:
        _event("error", "scheduler", "Scheduler worker recovery failed.", {"error": str(exc)[:500]})
        actions.append({"action": "restart_scheduler_thread", "status": "failed", "detail": str(exc)[:300]})

    failed = sum(1 for item in checks if item["status"] == "error")
    warning = sum(1 for item in checks if item["status"] == "warning")
    report = {
        "status": "error" if failed else "warning" if warning else "ok",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "actions": actions,
        "safety": {"database_auto_repair": False, "arbitrary_process_restart": False, "source_code_changes": False, "approval_bypass": False},
    }
    with _lock:
        _last_cycle = time.time()
        _last_report = report
    return report


def supervisor_status(limit=30):
    bounded = max(1, min(int(limit), 100))
    db_error = None
    try:
        _ensure_db()
        with connect() as conn:
            events = conn.execute(
                "SELECT id,created_at,severity,category,summary,details FROM supervisor_events ORDER BY id DESC LIMIT ?",
                (bounded,),
            ).fetchall()
    except Exception as exc:
        events = []
        db_error = type(exc).__name__ + ": " + str(exc)[:300]
    decoded = []
    for item in events:
        value = dict(item)
        try:
            value["details"] = json.loads(value["details"])
        except (TypeError, ValueError):
            value["details"] = {}
        decoded.append(value)
    with _lock:
        report = dict(_last_report)
        report["checks"] = list(_last_report.get("checks", []))
        report["actions"] = list(_last_report.get("actions", []))
        last_cycle = _last_cycle
    if db_error:
        report["status"] = "error"
        report["database_access_error"] = db_error
    try:
        enabled = bool_value("background_self_check_enabled", True)
        auto_resolver = bool_value("auto_error_resolver_enabled", True)
        interval = int_value("background_interval_minutes", 15)
    except Exception:
        enabled, auto_resolver, interval = True, True, 15
    return {
        "enabled": enabled,
        "auto_error_resolver_enabled": auto_resolver,
        "interval_minutes": interval,
        "worker_alive": bool(_thread and _thread.is_alive() and not _stop.is_set()),
        "last_cycle_epoch": last_cycle,
        "latest": report,
        "events": decoded,
        "limitations": ["Only Nano-owned scheduler worker restart is automatic.", "Database, model service, permissions, and source code are never auto-modified."],
    }


def _loop():
    next_run = 0.0
    while not _stop.is_set():
        interval = max(60, int_value("background_interval_minutes", 15) * 60)
        if bool_value("background_self_check_enabled", True):
            now = time.monotonic()
            if now >= next_run:
                try:
                    run_supervisor_cycle()
                except Exception as exc:
                    try:
                        _event("error", "supervisor", "Background health cycle failed.", {"error": str(exc)[:500]})
                    except Exception:
                        pass
                next_run = time.monotonic() + interval
        _stop.wait(min(1, interval))


def start_supervisor():
    global _thread
    with _lock:
        if _thread and _thread.is_alive():
            return
        _stop.clear()
        _thread = threading.Thread(target=_loop, name="nano-supervisor", daemon=True)
        _thread.start()


def stop_supervisor():
    _stop.set()
    with _lock:
        worker = _thread
    if worker and worker.is_alive():
        worker.join(timeout=2)
