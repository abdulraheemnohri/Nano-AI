"""Persistent interval scheduler with bounded retry and crash recovery."""
import json
import threading
import time
from datetime import datetime, timedelta, timezone
from .db import connect, run, rows

_lock = threading.RLock()
_thread = None
_stop = threading.Event()
_LEASE_SECONDS = 900
_MAX_BACKOFF_SECONDS = 3600


def _now():
    return datetime.now(timezone.utc)


def _ensure_column(connection, table, name, declaration):
    existing = {row["name"] for row in connection.execute("PRAGMA table_info(" + table + ")")}
    if name not in existing:
        connection.execute("ALTER TABLE " + table + " ADD COLUMN " + name + " " + declaration)


def _retry_delay(base_seconds, attempt):
    return min(max(1, int(base_seconds)) * (2 ** max(0, int(attempt) - 1)), _MAX_BACKOFF_SECONDS)


def init_scheduler_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS scheduled_jobs(
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, job_type TEXT NOT NULL,
          payload TEXT NOT NULL, interval_seconds INTEGER NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
          next_run_at TEXT NOT NULL, last_run_at TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS scheduled_runs(
          id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL, status TEXT NOT NULL,
          result TEXT, started_at TEXT DEFAULT CURRENT_TIMESTAMP, finished_at TEXT,
          FOREIGN KEY(job_id) REFERENCES scheduled_jobs(id));
        CREATE INDEX IF NOT EXISTS idx_scheduled_due ON scheduled_jobs(enabled,next_run_at);
        """)
        _ensure_column(c, "scheduled_jobs", "attempt_count", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(c, "scheduled_jobs", "max_attempts", "INTEGER NOT NULL DEFAULT 3")
        _ensure_column(c, "scheduled_jobs", "retry_delay_seconds", "INTEGER NOT NULL DEFAULT 60")
        _ensure_column(c, "scheduled_jobs", "claimed_at", "TEXT")
        _ensure_column(c, "scheduled_jobs", "last_error", "TEXT")
        _ensure_column(c, "scheduled_jobs", "timeout_seconds", "INTEGER NOT NULL DEFAULT 300")
        _ensure_column(c, "scheduled_runs", "attempt", "INTEGER NOT NULL DEFAULT 1")
    _recover_interrupted_runs()


def _recover_interrupted_runs():
    """Mark work left running by a crashed process and safely schedule a retry."""
    now = _now()
    with connect() as c:
        interrupted = c.execute(
            "SELECT id,job_id,attempt FROM scheduled_runs WHERE status='running'"
        ).fetchall()
        for item in interrupted:
            c.execute(
                "UPDATE scheduled_runs SET status='interrupted',result=?,finished_at=CURRENT_TIMESTAMP WHERE id=? AND status='running'",
                ("Scheduler process stopped before this attempt completed.", item["id"]),
            )
            job = c.execute("SELECT * FROM scheduled_jobs WHERE id=?", (item["job_id"],)).fetchone()
            if not job:
                continue
            attempt = max(int(item["attempt"] or 1), int(job["attempt_count"] or 0) + 1)
            if job["enabled"] and attempt < int(job["max_attempts"]):
                delay = _retry_delay(job["retry_delay_seconds"], attempt)
                next_at = (now + timedelta(seconds=delay)).isoformat()
                next_attempt_count = attempt
                error = "Previous run was interrupted; retry scheduled."
            else:
                next_at = (now + timedelta(seconds=int(job["interval_seconds"]))).isoformat()
                next_attempt_count = 0
                error = "Previous run was interrupted; retry limit reached." if job["enabled"] else "Previous run was interrupted while job was paused."
            c.execute(
                "UPDATE scheduled_jobs SET next_run_at=?,attempt_count=?,claimed_at=NULL,last_error=? WHERE id=?",
                (next_at, next_attempt_count, error, item["job_id"]),
            )
        # Also clear orphaned claims if a process died between claim and run-row insertion.
        c.execute(
            "UPDATE scheduled_jobs SET claimed_at=NULL,next_run_at=? "
            "WHERE claimed_at IS NOT NULL AND id NOT IN (SELECT job_id FROM scheduled_runs WHERE status='running')",
            (now.isoformat(),),
        )


def list_jobs():
    return rows("SELECT * FROM scheduled_jobs ORDER BY id DESC")


def list_runs(job_id=None, limit=100):
    bounded = max(1, min(int(limit), 500))
    if job_id is None:
        return rows("SELECT * FROM scheduled_runs ORDER BY id DESC LIMIT ?", (bounded,))
    return rows("SELECT * FROM scheduled_runs WHERE job_id=? ORDER BY id DESC LIMIT ?", (job_id, bounded))


def create_job(name, job_type, payload, interval_seconds, enabled=True, max_attempts=3, retry_delay_seconds=60, timeout_seconds=300):
    name = str(name or "").strip()[:100]
    if not name:
        raise ValueError("Job name is required.")
    if job_type != "assistant_prompt":
        raise ValueError("Supported job_type is assistant_prompt.")
    if not isinstance(payload, dict) or not str(payload.get("prompt", "")).strip():
        raise ValueError("assistant_prompt jobs require a non-empty prompt.")
    prompt = str(payload["prompt"]).strip()
    if len(prompt) > 8000:
        raise ValueError("Prompt is limited to 8000 characters.")
    if isinstance(interval_seconds, bool) or not isinstance(interval_seconds, int) or not 60 <= interval_seconds <= 31536000:
        raise ValueError("interval_seconds must be between 60 and 31536000.")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= 10:
        raise ValueError("max_attempts must be between 1 and 10.")
    if isinstance(retry_delay_seconds, bool) or not isinstance(retry_delay_seconds, int) or not 5 <= retry_delay_seconds <= 3600:
        raise ValueError("retry_delay_seconds must be between 5 and 3600.")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or not 5 <= timeout_seconds <= 86400:
        raise ValueError("timeout_seconds must be between 5 and 86400.")
    next_at = (_now() + timedelta(seconds=interval_seconds)).isoformat()
    jid = run(
        "INSERT INTO scheduled_jobs(name,job_type,payload,interval_seconds,enabled,next_run_at,max_attempts,retry_delay_seconds,timeout_seconds) VALUES(?,?,?,?,?,?,?,?,?)",
        (name, job_type, json.dumps({"prompt": prompt}, ensure_ascii=False), interval_seconds, 1 if enabled else 0, next_at, max_attempts, retry_delay_seconds, timeout_seconds),
    )
    return next(j for j in list_jobs() if j["id"] == jid)


def update_job(job_id, enabled):
    if not rows("SELECT id FROM scheduled_jobs WHERE id=?", (job_id,)):
        raise KeyError("Scheduled job not found.")
    run("UPDATE scheduled_jobs SET enabled=?,claimed_at=NULL WHERE id=?", (1 if enabled else 0, job_id))
    return next(j for j in list_jobs() if j["id"] == job_id)


def retry_job(job_id):
    with connect() as c:
        job = c.execute("SELECT id,enabled,claimed_at FROM scheduled_jobs WHERE id=?", (job_id,)).fetchone()
        if not job:
            raise KeyError("Scheduled job not found.")
        running = c.execute("SELECT 1 FROM scheduled_runs WHERE job_id=? AND status='running' LIMIT 1", (job_id,)).fetchone()
        if job["claimed_at"] or running:
            raise ValueError("Scheduled job is already running; wait for the current attempt to finish.")
        c.execute(
            "UPDATE scheduled_jobs SET enabled=1,attempt_count=0,claimed_at=NULL,last_error=NULL,next_run_at=? WHERE id=?",
            (_now().isoformat(), job_id),
        )
    return next(j for j in list_jobs() if j["id"] == job_id)


def delete_job(job_id):
    with connect() as c:
        c.execute("DELETE FROM scheduled_runs WHERE job_id=?", (job_id,))
        c.execute("DELETE FROM scheduled_jobs WHERE id=?", (job_id,))
    return {"ok": True}


class JobTimeoutError(RuntimeError):
    """Raised when a scheduled prompt exceeds its per-job hard timeout."""


def _execute_prompt(job, payload):
    """Run one assistant prompt with a per-job hard timeout.

    The model request runs in a daemon worker thread. If it exceeds the
    job timeout the attempt is recorded as an error and the normal bounded
    retry policy applies. The abandoned worker thread is not forcibly
    killed; it is left to finish or die with the process.
    """
    timeout = int(job.get("timeout_seconds") or 300)
    outcome = {}

    def _worker():
        try:
            from .core import respond
            cid = run("INSERT INTO conversations(title) VALUES(?)", ("Scheduled: " + job["name"],))
            outcome["result"] = respond(cid, "[Scheduled task: " + job["name"] + "]\n" + payload["prompt"])
        except BaseException as exc:
            outcome["error"] = exc

    worker = threading.Thread(target=_worker, name="nano-scheduler-job", daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise JobTimeoutError(f"Job timed out after {timeout} seconds.")
    if "error" in outcome:
        raise outcome["error"]
    return outcome.get("result")


def run_job(job):
    attempt = int(job.get("attempt_count", 0)) + 1
    started = run(
        "INSERT INTO scheduled_runs(job_id,status,result,attempt) VALUES(?,?,?,?)",
        (job["id"], "running", "", attempt),
    )
    try:
        payload = json.loads(job["payload"])
        result = _execute_prompt(job, payload)
        run(
            "UPDATE scheduled_runs SET status=?,result=?,finished_at=CURRENT_TIMESTAMP WHERE id=?",
            ("complete", str(result)[:12000], started),
        )
        run(
            "UPDATE scheduled_jobs SET last_run_at=CURRENT_TIMESTAMP,next_run_at=?,attempt_count=0,claimed_at=NULL,last_error=NULL WHERE id=?",
            ((_now() + timedelta(seconds=int(job["interval_seconds"]))).isoformat(), job["id"]),
        )
        return {"run_id": started, "status": "complete", "attempt": attempt}
    except Exception as exc:
        error = (type(exc).__name__ + ": " + str(exc))[:2000]
        run(
            "UPDATE scheduled_runs SET status=?,result=?,finished_at=CURRENT_TIMESTAMP WHERE id=?",
            ("error", error, started),
        )
        max_attempts = max(1, min(10, int(job.get("max_attempts", 3))))
        if attempt < max_attempts and bool(job.get("enabled", 1)):
            delay = _retry_delay(job.get("retry_delay_seconds", 60), attempt)
            next_at = (_now() + timedelta(seconds=delay)).isoformat()
            run(
                "UPDATE scheduled_jobs SET next_run_at=?,attempt_count=?,claimed_at=NULL,last_error=? WHERE id=?",
                (next_at, attempt, error, job["id"]),
            )
            status = "retry_scheduled"
        else:
            next_at = (_now() + timedelta(seconds=int(job["interval_seconds"]))).isoformat()
            run(
                "UPDATE scheduled_jobs SET last_run_at=CURRENT_TIMESTAMP,next_run_at=?,attempt_count=0,claimed_at=NULL,last_error=? WHERE id=?",
                (next_at, error, job["id"]),
            )
            status = "failed"
        return {"run_id": started, "status": status, "attempt": attempt, "error": error}


def _loop():
    while not _stop.wait(2):
        try:
            due = rows(
                "SELECT * FROM scheduled_jobs WHERE enabled=1 AND claimed_at IS NULL AND next_run_at<=? ORDER BY next_run_at LIMIT 5",
                (_now().isoformat(),),
            )
            for job in due:
                lease_until = (_now() + timedelta(seconds=_LEASE_SECONDS)).isoformat()
                with connect() as conn:
                    cur = conn.execute(
                        "UPDATE scheduled_jobs SET claimed_at=CURRENT_TIMESTAMP,next_run_at=? WHERE id=? AND enabled=1 AND claimed_at IS NULL AND next_run_at=?",
                        (lease_until, job["id"], job["next_run_at"]),
                    )
                    claimed = cur.rowcount == 1
                if claimed:
                    run_job(job)
        except Exception:
            time.sleep(1)


def start_scheduler():
    global _thread
    init_scheduler_db()
    with _lock:
        if _thread and _thread.is_alive():
            if not _stop.is_set():
                return
            _thread.join(timeout=2.5)
        _stop.clear()
        _thread = threading.Thread(target=_loop, name="nano-scheduler", daemon=True)
        _thread.start()


def stop_scheduler():
    _stop.set()
