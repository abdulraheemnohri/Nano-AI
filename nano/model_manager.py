import hashlib
import shutil
import subprocess
import threading
import re
import time
import tempfile
import os
from . import config
from .runtime import registry_models, litert_lm_binary

MODEL_REPO="litert-community/Qwen3-1.7B"
MODEL_FILE="Qwen3-1.7B_dynamic_wi4b32_afp32.litertlm"
MODEL_URL=f"https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}?download=true"

def default_model_path():
    return str(config.MODEL_DIR / config.MODEL_NAME)

def registry_list():
    return registry_models()

def validate_import_request(repo, filename, model_id=None):
    """Validate user-controlled model import identifiers before invoking the CLI."""
    repo = str(repo or "").strip()
    filename = str(filename or "").strip()
    target = str(model_id or config.LITERT_MODEL).strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}/[A-Za-z0-9][A-Za-z0-9._-]{0,95}", repo):
        raise ValueError("Repository must use the Hugging Face owner/repository format.")
    if not filename or filename in {".", ".."} or "/" in filename or filename.endswith(".") or chr(92) in filename or not filename.lower().endswith(".litertlm"):
        raise ValueError("Filename must be a single .litertlm artifact filename.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", target):
        raise ValueError("Model ID may contain only letters, numbers, dots, underscores, and hyphens.")
    return repo, filename, target


def import_model(repo=MODEL_REPO, filename=MODEL_FILE, model_id=None):
    repo, filename, target = validate_import_request(repo, filename, model_id)
    binary = litert_lm_binary()
    if not binary:
        raise RuntimeError("litert-lm was not found. Install it with: python -m pip install -U litert-lm")
    try:
        subprocess.run(
            [binary, "import", f"--from-huggingface-repo={repo}", filename, target],
            check=True,
            timeout=7200,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Model import timed out after 2 hours. Check network connectivity and LiteRT-LM logs.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"LiteRT-LM model import failed with exit code {exc.returncode}.") from exc
    return target

def remove_model(model_id):
    binary = litert_lm_binary()
    if not binary:
        raise RuntimeError("litert-lm was not found.")
    # LiteRT-LM registry removal syntax can vary by release; do not invent a destructive command.
    raise RuntimeError("Model deletion is intentionally not automated; use the LiteRT-LM version's documented registry management command.")

def info():
    p=default_model_path()
    return {
        "runtime":"litert-lm","name":config.MODEL_NAME,"registry_model":config.LITERT_MODEL,
        "local_path":p,"local_file_installed":__import__("os").path.exists(p),
        "local_file_size":__import__("os").path.getsize(p) if __import__("os").path.exists(p) else 0,
        "registry_models":registry_list(),"url":MODEL_URL,"repository":MODEL_REPO
    }

def sha256(path=None):
    h=hashlib.sha256()
    with open(path or default_model_path(),"rb") as f:
        for c in iter(lambda:f.read(1048576),b""): h.update(c)
    return h.hexdigest()


_AUTO_LOCK = threading.Lock()
_AUTO_STATE = {"status": "idle", "message": "Model setup has not been started.", "model_id": None, "progress": 0, "phase": "idle", "cancel_requested": False}
_ACTIVE_PROCESS = None
_CANCEL_EVENT = threading.Event()

def _set_task(**values):
    with _AUTO_LOCK:
        _AUTO_STATE.update(values)

def _tracked_import(repo, filename, target):
    """Run import with cancellable process management and best-effort progress reporting."""
    global _ACTIVE_PROCESS
    binary = litert_lm_binary()
    if not binary:
        raise RuntimeError("litert-lm was not found. Install it with: python -m pip install -U litert-lm")
    command = [binary, "import", f"--from-huggingface-repo={repo}", filename, target]
    started = time.monotonic()
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8", errors="replace") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, text=True)
        with _AUTO_LOCK:
            _ACTIVE_PROCESS = process
        seen = 0
        try:
            while process.poll() is None:
                if _CANCEL_EVENT.wait(0.5):
                    process.terminate()
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill(); process.wait(timeout=5)
                    _set_task(status="cancelled", message="Model import cancelled by user.", phase="cancelled", cancel_requested=True)
                    raise RuntimeError("Model import cancelled by user.")
                log.flush()
                log.seek(seen)
                chunk = log.read()
                seen = log.tell()
                match = re.findall(r"(?<!\d)(\d{1,3})\s*%", chunk)
                if match:
                    percent = max(0,min(99,int(match[-1])))
                    _set_task(progress=percent, phase="downloading", message=f"LiteRT-LM reports {percent}% progress.")
                else:
                    estimate = min(90, 5 + int((time.monotonic()-started)/12))
                    _set_task(progress=max(5,estimate), phase="importing", message=f"Import running; estimated progress {max(5,estimate)}% (CLI did not expose a percentage).")
                time.sleep(0.1)
            if _CANCEL_EVENT.is_set():
                _set_task(status="cancelled", message="Model import cancelled by user.", phase="cancelled", cancel_requested=True)
                raise RuntimeError("Model import cancelled by user.")
            log.flush()
            log.seek(max(0, os.fstat(log.fileno()).st_size - 5000))
            tail = log.read()[-4000:]
            if process.returncode:
                raise RuntimeError(f"LiteRT-LM model import failed with exit code {process.returncode}. {tail}")
            _set_task(progress=100, phase="complete", message="Model import completed.")
            return target
        finally:
            with _AUTO_LOCK:
                _ACTIVE_PROCESS = None

def cancel_import_task():
    with _AUTO_LOCK:
        if _AUTO_STATE.get("status") not in {"queued", "running"}:
            return dict(_AUTO_STATE)
        _CANCEL_EVENT.set()
        proc = _ACTIVE_PROCESS
        _AUTO_STATE.update(cancel_requested=True, message="Cancellation requested; stopping the LiteRT-LM process.")
    if proc is not None:
        try: proc.terminate()
        except OSError: pass
    return auto_setup_status()


def auto_setup_status():
    with _AUTO_LOCK:
        return dict(_AUTO_STATE)


def _auto_setup_worker():
    try:
        if _CANCEL_EVENT.is_set():
            _set_task(status="cancelled",message="Model setup cancelled before starting.",phase="cancelled",cancel_requested=True)
            return
        with _AUTO_LOCK:
            _AUTO_STATE.update(status="running", message="Checking LiteRT-LM and model registry.", model_id=config.LITERT_MODEL, progress=2, phase="checking", cancel_requested=False)
        binary = litert_lm_binary()
        if not binary:
            raise RuntimeError("LiteRT-LM CLI is missing. Install it with: python -m pip install -U litert-lm")
        registry = registry_models()
        if any(config.LITERT_MODEL.lower() in str(item.get("raw", "")).lower() for item in registry):
            with _AUTO_LOCK:
                _AUTO_STATE.update(status="complete", message="Configured model already appears in the LiteRT-LM registry.", model_id=config.LITERT_MODEL, progress=100, phase="complete")
            return
        with _AUTO_LOCK:
            _AUTO_STATE.update(status="running", message="Importing the default Qwen3 1.7B model. This may take a while and use about 1 GB of storage and network data.", model_id=config.LITERT_MODEL)
        if _CANCEL_EVENT.is_set(): raise RuntimeError("Model import cancelled by user.")
        imported = _tracked_import(MODEL_REPO, MODEL_FILE, config.LITERT_MODEL)
        with _AUTO_LOCK:
            if _AUTO_STATE["status"] != "cancelled":
                _AUTO_STATE.update(status="complete", message="Model import command completed. Check runtime status before chatting.", model_id=imported, progress=100, phase="complete")
    except Exception as exc:
        with _AUTO_LOCK:
            if _CANCEL_EVENT.is_set():
                _AUTO_STATE.update(status="cancelled", message="Model setup cancelled by user.", phase="cancelled", cancel_requested=True)
            elif _AUTO_STATE["status"] != "cancelled":
                _AUTO_STATE.update(status="error", message=str(exc)[:500], model_id=config.LITERT_MODEL, phase="error")


def start_auto_setup():
    # Treat queued and running as active so rapid clicks cannot launch concurrent imports.
    with _AUTO_LOCK:
        if _AUTO_STATE["status"] in {"queued", "running"}:
            return dict(_AUTO_STATE)
        _CANCEL_EVENT.clear()
        _AUTO_STATE.update(status="queued", message="Model setup queued.", model_id=config.LITERT_MODEL, progress=0, phase="queued", cancel_requested=False)
        thread = threading.Thread(target=_auto_setup_worker, name="nano-model-setup", daemon=True)
        thread.start()
        return dict(_AUTO_STATE)


def start_import_task(repo, filename, model_id=None):
    """Queue a validated custom model import without blocking the HTTP request."""
    repo, filename, target = validate_import_request(repo, filename, model_id)
    with _AUTO_LOCK:
        if _AUTO_STATE["status"] in {"queued", "running"}:
            raise RuntimeError("A model setup/import task is already active.")
        _CANCEL_EVENT.clear()
        _AUTO_STATE.update(status="queued", message=f"Custom model import queued for {target}.", model_id=target, progress=0, phase="queued", cancel_requested=False)
        thread = threading.Thread(
            target=_custom_import_worker,
            args=(repo, filename, target),
            name="nano-custom-model-import",
            daemon=True,
        )
        thread.start()
        return dict(_AUTO_STATE)


def _custom_import_worker(repo, filename, target):
    try:
        if _CANCEL_EVENT.is_set():
            _set_task(status="cancelled",message="Model import cancelled before starting.",phase="cancelled",cancel_requested=True)
            return
        with _AUTO_LOCK:
            _AUTO_STATE.update(status="running", message=f"Importing {repo}/{filename}. This may take a while.", model_id=target, progress=5, phase="importing", cancel_requested=False)
        if _CANCEL_EVENT.is_set(): raise RuntimeError("Model import cancelled by user.")
        imported = _tracked_import(repo, filename, target)
        with _AUTO_LOCK:
            if _AUTO_STATE["status"] != "cancelled":
                _AUTO_STATE.update(status="complete", message="Custom model import command completed. Check runtime status before chatting.", model_id=imported, progress=100, phase="complete")
    except Exception as exc:
        with _AUTO_LOCK:
            if _CANCEL_EVENT.is_set():
                _AUTO_STATE.update(status="cancelled", message="Model import cancelled by user.", model_id=target, phase="cancelled", cancel_requested=True)
            elif _AUTO_STATE["status"] != "cancelled":
                _AUTO_STATE.update(status="error", message=str(exc)[:500], model_id=target, phase="error")
