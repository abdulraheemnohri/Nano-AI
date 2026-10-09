"""Read-only diagnostics for Nano AI's local installation."""
import importlib.util
import sqlite3
import sys
import tempfile
from . import config
from .runtime import status as runtime_status, model_readiness
from .security import auth_policy


def _check(name, state, detail):
    return {"name": name, "status": state, "detail": str(detail)}


def run_checks():
    """Return actionable health checks without creating a database or starting services."""
    checks = []
    checks.append(_check(
        "python",
        "ok" if sys.version_info >= (3, 10) else "fail",
        f"Python {sys.version_info.major}.{sys.version_info.minor}; Python 3.10+ required.",
    ))

    for label, path in (
        ("data directory", config.DATA_DIR),
        ("model directory", config.MODEL_DIR),
        ("skills directory", config.SKILLS_DIR),
    ):
        try:
            if not path.is_dir():
                checks.append(_check(label, "fail", f"Directory does not exist: {path}"))
                continue
            with tempfile.NamedTemporaryFile(prefix=".nano-doctor-", dir=path, delete=True):
                pass
            checks.append(_check(label, "ok", f"Writable: {path}"))
        except OSError as exc:
            checks.append(_check(label, "fail", f"Not writable: {path} ({exc})"))

    db_path = config.DB_PATH
    if not db_path.is_file():
        checks.append(_check("database", "warn", f"Database not initialized at {db_path}; run nano-ai init."))
    else:
        try:
            with sqlite3.connect(str(db_path), timeout=3) as conn:
                integrity = conn.execute("PRAGMA integrity_check").fetchone()
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            required = {"conversations", "messages", "memories", "settings"}
            missing = sorted(required - tables)
            if not integrity or integrity[0] != "ok":
                checks.append(_check("database", "fail", "SQLite integrity_check did not return ok."))
            elif missing:
                checks.append(_check("database", "fail", "Required tables are missing: " + ", ".join(missing)))
            else:
                checks.append(_check("database", "ok", f"SQLite integrity check passed: {db_path}"))
        except (OSError, sqlite3.Error) as exc:
            checks.append(_check("database", "fail", f"Database could not be checked: {exc}"))

    policy = auth_policy()
    if policy["remote_host"] and not policy["token_configured"]:
        checks.append(_check("API security", "fail", "Remote binding requires NANO_API_TOKEN."))
    elif policy["remote_host"]:
        checks.append(_check("API security", "warn", "Token is configured for remote binding; TLS, firewall, and proxy protections must also be verified."))
    elif policy["token_configured"]:
        checks.append(_check("API security", "ok", "API token is configured."))
    else:
        checks.append(_check("API security", "ok", "Loopback binding detected; no remote API token is configured."))

    runtime = runtime_status()
    checks.append(_check(
        "LiteRT-LM CLI",
        "ok" if runtime.get("binary") else "warn",
        "LiteRT-LM CLI found." if runtime.get("binary") else "CLI not found; install LiteRT-LM before model setup or inference.",
    ))
    readiness = model_readiness(runtime)
    checks.append(_check("model endpoint", readiness["status"], readiness["detail"]))

    checks.append(_check(
        "optional browser",
        "ok" if importlib.util.find_spec("playwright") else "info",
        "Playwright is installed." if importlib.util.find_spec("playwright") else "Playwright is optional and not installed.",
    ))
    try:
        from .voice import voice_status
        voice = voice_status()
        checks.append(_check(
            "optional voice",
            "ok" if voice.get("stt", {}).get("ready") or voice.get("tts", {}).get("ready") else "info",
            "At least one offline voice path is ready." if voice.get("stt", {}).get("ready") or voice.get("tts", {}).get("ready") else "Voice is optional; configure local Vosk/Piper dependencies and assets if needed.",
        ))
    except Exception:
        checks.append(_check("optional voice", "info", "Voice diagnostics unavailable; core Nano AI can run without optional voice dependencies."))

    counts = {state: sum(1 for item in checks if item["status"] == state) for state in ("ok", "info", "warn", "fail")}
    overall = "fail" if counts["fail"] else "warn" if counts["warn"] else "ok"
    return {
        "overall": overall,
        "summary": counts,
        "checks": checks,
        "read_only": True,
        "note": "Diagnostics do not install packages, download models, modify settings, or start services.",
    }
