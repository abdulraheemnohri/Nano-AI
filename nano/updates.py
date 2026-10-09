"""Safe, explicit GitHub update lifecycle for the official Nano AI checkout.

Checking updates is read-only. Applying an update requires an explicit approval,
a clean working tree, the main branch, and the expected official GitHub origin.
The process never installs dependencies or restarts the running service automatically.
"""
import json
import subprocess
import urllib.request
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
    _git("merge", "--ff-only", "refs/remotes/origin/main", timeout=60)
    after = _checkout()
    return {
        "updated": after["local_sha"] == remote_sha,
        "previous_sha": before["local_sha"],
        "current_sha": after["local_sha"],
        "restart_required": True,
        "dependency_install_required": "Review pyproject.toml and release notes; install dependencies manually if they changed.",
        "message": "Fast-forward update applied. Restart Nano AI to load the new code.",
    }
