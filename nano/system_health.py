"""Live, read-only system health snapshot for the Nano AI dashboard."""
import sqlite3
from datetime import datetime, timezone

from . import config, scheduler
from .db import rows
from .runtime import status as runtime_status
from .voice import voice_status


def system_health():
    checks = []
    counts = {"conversations": 0, "messages": 0, "memories": 0, "active_memories": 0}
    db_state = "warn"
    db_detail = "Database has not been initialized."
    try:
        with sqlite3.connect(str(config.DB_PATH), timeout=2) as conn:
            conn.row_factory = sqlite3.Row
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
            tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            required = {"conversations", "messages", "memories", "settings"}
            missing = sorted(required - tables)
            if integrity and integrity[0] == "ok" and not missing:
                db_state = "ok"
                db_detail = "SQLite integrity and required tables are healthy."
                for key, table in (("conversations", "conversations"), ("messages", "messages"), ("memories", "memories")):
                    counts[key] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                counts["active_memories"] = int(conn.execute("SELECT COUNT(*) FROM memories WHERE status='active'").fetchone()[0])
            else:
                db_state = "fail"
                db_detail = "SQLite integrity check failed." if not integrity or integrity[0] != "ok" else "Missing required tables: " + ", ".join(missing)
    except (OSError, sqlite3.Error) as exc:
        db_state = "fail" if config.DB_PATH.exists() else "warn"
        db_detail = f"Database check failed: {type(exc).__name__}: {exc}"[:500]
    checks.append({"name": "database", "status": db_state, "detail": db_detail, "counts": counts})

    try:
        runtime = runtime_status()
        model_state = "ok" if runtime.get("reachable") else "warn"
        checks.append({
            "name": "model",
            "status": model_state,
            "detail": "LiteRT-LM endpoint reachable." if runtime.get("reachable") else "LiteRT-LM endpoint is not reachable.",
            "binary_found": bool(runtime.get("binary")),
            "configured_url": runtime.get("configured_url", config.LITERT_URL),
            "model": runtime.get("model", config.LITERT_MODEL),
            "loaded_models": runtime.get("models", [])[:20],
        })
    except Exception as exc:
        checks.append({"name": "model", "status": "warn", "detail": f"Runtime check failed: {type(exc).__name__}: {exc}"[:500]})

    thread = getattr(scheduler, "_thread", None)
    stop_event = getattr(scheduler, "_stop", None)
    scheduler_running = bool(thread and thread.is_alive() and stop_event and not stop_event.is_set())
    checks.append({
        "name": "scheduler",
        "status": "ok" if scheduler_running else "warn",
        "detail": "Scheduler worker thread is running." if scheduler_running else "Scheduler worker thread is not running in this process.",
        "worker_alive": bool(thread and thread.is_alive()),
    })

    try:
        jobs = rows("SELECT id,name,enabled,next_run_at,last_run_at,last_error,attempt_count,max_attempts FROM scheduled_jobs ORDER BY id DESC LIMIT 100")
        runs = rows("SELECT id,job_id,status,result,started_at,finished_at,attempt FROM scheduled_runs ORDER BY id DESC LIMIT 100")
        job_state = "ok"
        job_detail = f"{len(jobs)} recent jobs; {sum(1 for j in jobs if j.get('enabled'))} enabled."
        recent_errors = [
            {"run_id": item["id"], "job_id": item["job_id"], "status": item["status"],
             "error": str(item.get("result") or "")[:1000], "started_at": item.get("started_at"),
             "finished_at": item.get("finished_at"), "attempt": item.get("attempt")}
            for item in runs if item.get("status") in {"error", "interrupted"}
        ][:10]
        failed_jobs = sum(1 for j in jobs if j.get("last_error"))
        checks.append({
            "name": "background_tasks", "status": "warn" if failed_jobs or recent_errors else job_state,
            "detail": job_detail, "jobs_total": len(jobs),
            "jobs_enabled": sum(1 for j in jobs if j.get("enabled")),
            "jobs_with_errors": failed_jobs, "recent_errors": recent_errors,
        })
    except sqlite3.Error as exc:
        checks.append({"name": "background_tasks", "status": "warn", "detail": f"Scheduler tables unavailable: {exc}"[:500], "jobs_total": 0, "jobs_enabled": 0, "jobs_with_errors": 0, "recent_errors": []})

    try:
        voice = voice_status()
        stt = voice.get("stt", {})
        tts = voice.get("tts", {})
        checks.append({
            "name": "voice",
            "status": "ok" if stt.get("ready") or tts.get("ready") else "info",
            "detail": "At least one offline voice path is ready." if stt.get("ready") or tts.get("ready") else "Optional Vosk/Piper dependencies or local voice assets are not fully configured.",
            "stt_ready": bool(stt.get("ready")), "tts_ready": bool(tts.get("ready")),
        })
    except Exception as exc:
        checks.append({"name": "voice", "status": "info", "detail": f"Optional voice status unavailable: {type(exc).__name__}"})

    states = {item["status"] for item in checks}
    overall = "fail" if "fail" in states else "warn" if "warn" in states else "ok"
    return {
        "overall": overall,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "read_only": True,
        "note": "Live process snapshot; it does not restart workers, change settings, or repair data.",
    }
