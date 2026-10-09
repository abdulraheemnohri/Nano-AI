"""Safe, explicit GitHub update lifecycle for the official Nano AI checkout.

Checking updates is read-only. Applying an update requires an explicit approval,
a clean working tree, the main branch, and the expected official GitHub origin.
The process never installs dependencies or restarts the running service automatically.
"""
import json
import subprocess
import urllib.request
from pathlib import Path
from . import config

OWNER = "abdulraheemnohri"
REPOSITORY = "Nano-AI"
API_URL = f"https://api.github.com/repos/{OWNER}/{REPOSITORY}/commits/main"
EXPECTED_ORIGIN = {
    f"https://github.com/{OWNER}/{REPOSITORY}.git",
    f"https://github.com/{OWNER}/{REPOSITORY}",
    f"git@github.com:{OWNER}/{REPOSITORY}.git",
    f"ssh://git@github.com/{OWNER}/{REPOSITORY}.git",
}


def _git(*args, timeout=20):
    try:
        result = subprocess.run(
            ["git", "-C", str(config.ROOT), *args],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Git operation failed: {exc}") from exc
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "Git command failed.")[-2000:])
    return result.stdout.strip()


def _checkout():
    if _git("rev-parse", "--is-inside-work-tree") != "true":
        raise RuntimeError("Nano root is not a Git checkout.")
    branch = _git("branch", "--show-current")
    head = _git("rev-parse", "HEAD")
    origin = _git("remote", "get-url", "origin")
    dirty = bool(_git("status", "--porcelain"))
    if origin not in EXPECTED_ORIGIN:
        raise RuntimeError("Update blocked: origin is not the expected official Nano AI GitHub repository.")
    return {"branch": branch, "local_sha": head, "dirty": dirty, "origin": origin}


def check_update():
    checkout = _checkout()
    request = urllib.request.Request(
        API_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Nano-AI-Updater"},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.loads(response.read(256_000).decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Could not check GitHub for updates: {exc}") from exc
    latest = str(data.get("sha", ""))
    if len(latest) != 40 or any(ch not in "0123456789abcdef" for ch in latest.lower()):
        raise RuntimeError("GitHub returned an invalid commit identifier.")
    return {
        **checkout,
        "repository": f"{OWNER}/{REPOSITORY}",
        "latest_sha": latest,
        "latest_url": data.get("html_url", f"https://github.com/{OWNER}/{REPOSITORY}/commit/{latest}"),
        "update_available": latest != checkout["local_sha"],
        "can_apply": checkout["branch"] == "main" and not checkout["dirty"],
        "policy": "Check is read-only. Apply requires explicit approval and a clean main branch; restart and dependency updates remain manual.",
    }


def apply_update(approved=False):
    if approved is not True:
        raise PermissionError("Explicit approval is required to apply a GitHub update.")
    before = check_update()
    if before["branch"] != "main":
        raise RuntimeError("Update blocked: checkout must be on main.")
    if before["dirty"]:
        raise RuntimeError("Update blocked: commit or back up local changes before updating.")
    if not before["update_available"]:
        return {"updated": False, "message": "Nano AI is already at the latest main commit.", **before}
    _git("fetch", "--no-tags", "origin", "main", timeout=60)
    remote_sha = _git("rev-parse", "refs/remotes/origin/main")
    if remote_sha != before["latest_sha"]:
        raise RuntimeError("GitHub main changed during the update check. Check again before applying.")
    previous_sha = before["local_sha"]
    database_snapshot = _snapshot_database()
    try:
        _git("merge", "--ff-only", "refs/remotes/origin/main", timeout=60)
        after = _checkout()
        if after["local_sha"] != remote_sha:
            raise RuntimeError("Updated checkout does not match the verified remote commit.")
        dependency_files = _git("diff", "--name-only", previous_sha, remote_sha, "--", "pyproject.toml", "requirements.txt", "requirements-dev.txt", "uv.lock", "poetry.lock")
        manifest = {"repository": f"{OWNER}/{REPOSITORY}", "previous_sha": previous_sha, "current_sha": remote_sha, "database_snapshot": database_snapshot, "dependency_files_changed": dependency_files.splitlines() if dependency_files else [], "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}
        _write_recovery_manifest(manifest)
    except Exception as exc:
        try:
            head = _git("rev-parse", "HEAD")
            if head != previous_sha and not _git("status", "--porcelain"):
                _git("reset", "--hard", previous_sha, timeout=60)
        except Exception:
            pass
        raise RuntimeError(f"Update did not complete safely: {exc}") from exc
    dependency_files = manifest["dependency_files_changed"]
    return {
        "updated": True, **manifest,
        "restart_required": True,
        "dependency_install_required": bool(dependency_files),
        "recovery_manifest": str(_recovery_paths()[1]),
        "message": "Fast-forward update applied. Review dependency changes and restart Nano AI manually.",
    }

# Recovery helpers are deliberately separate from the fast-forward update path.
def _recovery_paths():
    root = (config.DATA_DIR / "update-recovery").resolve()
    return root, root / "latest-update.json"


def _snapshot_database():
    import sqlite3
    from datetime import datetime, timezone
    root, _ = _recovery_paths()
    root.mkdir(parents=True, exist_ok=True)
    db_path = Path(config.DB_PATH)
    if not db_path.is_file():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    snapshot = root / ("nano-before-update-" + stamp + ".sqlite3")
    with sqlite3.connect(str(db_path), timeout=10) as source, sqlite3.connect(str(snapshot), timeout=10) as target:
        source.backup(target)
        check = target.execute("PRAGMA integrity_check").fetchone()
        if not check or check[0] != "ok":
            snapshot.unlink(missing_ok=True)
            raise RuntimeError("Pre-update database snapshot failed integrity_check.")
    return str(snapshot)


def _write_recovery_manifest(manifest):
    import json
    root, path = _recovery_paths()
    root.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(manifest, indent=2) + "\\n", encoding="utf-8")
    temp.replace(path)


def rollback_update(approved=False, restore_database=False):
    """Roll back only the last recorded updater change; database restore is separately opt-in."""
    import json
    import sqlite3
    from pathlib import Path
    if approved is not True:
        raise PermissionError("Explicit approval is required to roll back an update.")
    checkout = _checkout()
    if checkout["branch"] != "main" or checkout["dirty"]:
        raise RuntimeError("Rollback requires a clean main branch.")
    root, manifest_path = _recovery_paths()
    if not manifest_path.is_file():
        raise RuntimeError("No update recovery manifest exists.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError("Update recovery manifest is unreadable.") from exc
    previous = str(manifest.get("previous_sha", ""))
    updated = str(manifest.get("current_sha", ""))
    if checkout["local_sha"] != updated:
        raise RuntimeError("Rollback blocked: HEAD differs from the recorded update.")
    if len(previous) != 40 or len(updated) != 40:
        raise RuntimeError("Recovery manifest contains invalid commit identifiers.")
    _git("cat-file", "-e", previous + "^{commit}")
    snapshot = manifest.get("database_snapshot")
    if restore_database:
        snapshot_path = Path(snapshot).resolve() if snapshot else None
        if not snapshot_path or root.resolve() not in snapshot_path.parents or not snapshot_path.is_file():
            raise RuntimeError("A valid pre-update database snapshot is unavailable.")
        with sqlite3.connect(str(snapshot_path), timeout=10) as source:
            check = source.execute("PRAGMA integrity_check").fetchone()
            if not check or check[0] != "ok":
                raise RuntimeError("Database snapshot failed integrity_check.")
            db_path = Path(config.DB_PATH)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(db_path), timeout=10) as target:
                source.backup(target)
                after = target.execute("PRAGMA integrity_check").fetchone()
                if not after or after[0] != "ok":
                    raise RuntimeError("Restored database failed integrity_check.")
    _git("reset", "--hard", previous, timeout=60)
    return {
        "rolled_back": _git("rev-parse", "HEAD") == previous,
        "rolled_back_to": previous,
        "database_restored": bool(restore_database and snapshot),
        "restart_required": True,
        "message": "Code rollback completed. Restart Nano AI manually.",
    }
