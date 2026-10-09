"""Persistent interval scheduler for bounded assistant tasks."""
import json
import threading
import time
from datetime import datetime, timedelta, timezone
from .db import connect, run, rows

_lock = threading.RLock()
_thread = None
_stop = threading.Event()

def _now():
    return datetime.now(timezone.utc)

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

def list_jobs():
    return rows("SELECT * FROM scheduled_jobs ORDER BY id DESC")

def list_runs(job_id=None, limit=100):
    if job_id is None:
        return rows("SELECT * FROM scheduled_runs ORDER BY id DESC LIMIT ?", (max(1,min(int(limit),500)),))
    return rows("SELECT * FROM scheduled_runs WHERE job_id=? ORDER BY id DESC LIMIT ?", (job_id,max(1,min(int(limit),500))))

def create_job(name, job_type, payload, interval_seconds, enabled=True):
    name = str(name or "").strip()[:100]
    if not name: raise ValueError("Job name is required.")
    if job_type != "assistant_prompt": raise ValueError("Supported job_type is assistant_prompt.")
    if not isinstance(payload, dict) or not str(payload.get("prompt","")).strip():
        raise ValueError("assistant_prompt jobs require a non-empty prompt.")
    prompt = str(payload["prompt"]).strip()
    if len(prompt) > 8000: raise ValueError("Prompt is limited to 8000 characters.")
    if isinstance(interval_seconds, bool) or not isinstance(interval_seconds,int) or not 60 <= interval_seconds <= 31536000:
        raise ValueError("interval_seconds must be between 60 and 31536000.")
    next_at = (_now()+timedelta(seconds=interval_seconds)).isoformat()
    jid = run("INSERT INTO scheduled_jobs(name,job_type,payload,interval_seconds,enabled,next_run_at) VALUES(?,?,?,?,?,?)",
              (name,job_type,json.dumps({"prompt":prompt},ensure_ascii=False),interval_seconds,1 if enabled else 0,next_at))
    return next(j for j in list_jobs() if j["id"] == jid)

def update_job(job_id, enabled):
    if not rows("SELECT id FROM scheduled_jobs WHERE id=?", (job_id,)): raise KeyError("Scheduled job not found.")
    run("UPDATE scheduled_jobs SET enabled=? WHERE id=?", (1 if enabled else 0,job_id))
    return next(j for j in list_jobs() if j["id"] == job_id)

def delete_job(job_id):
    run("DELETE FROM scheduled_runs WHERE job_id=?", (job_id,))
    run("DELETE FROM scheduled_jobs WHERE id=?", (job_id,))
    return {"ok": True}

def run_job(job):
    started = run("INSERT INTO scheduled_runs(job_id,status,result) VALUES(?,?,?)", (job["id"],"running",""))
    try:
        from .core import respond
        cid = run("INSERT INTO conversations(title) VALUES(?)", ("Scheduled: "+job["name"],))
        payload = json.loads(job["payload"])
        result = respond(cid, "[Scheduled task: "+job["name"]+"]\n"+payload["prompt"])
        run("UPDATE scheduled_runs SET status=?,result=?,finished_at=CURRENT_TIMESTAMP WHERE id=?",
            ("complete",result[:12000],started))
        status = "complete"
    except Exception as exc:
        run("UPDATE scheduled_runs SET status=?,result=?,finished_at=CURRENT_TIMESTAMP WHERE id=?",
            ("error",str(exc)[:2000],started))
        status = "error"
    run("UPDATE scheduled_jobs SET last_run_at=CURRENT_TIMESTAMP,next_run_at=? WHERE id=?",
        ((_now()+timedelta(seconds=job["interval_seconds"])).isoformat(),job["id"]))
    return {"run_id":started,"status":status}

def _loop():
    while not _stop.wait(2):
        try:
            due = rows("SELECT * FROM scheduled_jobs WHERE enabled=1 AND next_run_at<=? ORDER BY next_run_at LIMIT 5", (_now().isoformat(),))
            for job in due:
                # Claim the due job before running to avoid duplicate workers in one process.
                with connect() as conn:
                    cur = conn.execute("UPDATE scheduled_jobs SET next_run_at=? WHERE id=? AND next_run_at=?",
                                       ((_now()+timedelta(days=3650)).isoformat(),job["id"],job["next_run_at"]))
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
            if not _stop.is_set(): return
            _thread.join(timeout=2.5)
        _stop.clear()
        _thread = threading.Thread(target=_loop,name="nano-scheduler",daemon=True)
        _thread.start()

def stop_scheduler():
    _stop.set()
