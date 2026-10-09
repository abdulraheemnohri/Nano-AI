import hashlib
import shutil
import subprocess
import threading
from . import config
from .runtime import registry_models, litert_lm_binary

MODEL_REPO="litert-community/Qwen3-1.7B"
MODEL_FILE="Qwen3-1.7B_dynamic_wi4b32_afp32.litertlm"
MODEL_URL=f"https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}?download=true"

def default_model_path():
    return str(config.MODEL_DIR / config.MODEL_NAME)

def registry_list():
    return registry_models()

def import_model(repo=MODEL_REPO, filename=MODEL_FILE, model_id=None):
    binary = litert_lm_binary()
    if not binary:
        raise RuntimeError("litert-lm was not found. Install it with: python -m pip install -U litert-lm")
    target = model_id or config.LITERT_MODEL
    subprocess.run([binary, "import", f"--from-huggingface-repo={repo}", filename, target], check=True)
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
_AUTO_STATE = {"status": "idle", "message": "Model setup has not been started.", "model_id": None}


def auto_setup_status():
    with _AUTO_LOCK:
        return dict(_AUTO_STATE)


def _auto_setup_worker():
    try:
        with _AUTO_LOCK:
            _AUTO_STATE.update(status="running", message="Checking LiteRT-LM and model registry.", model_id=config.LITERT_MODEL)
        binary = litert_lm_binary()
        if not binary:
            raise RuntimeError("LiteRT-LM CLI is missing. Install it with: python -m pip install -U litert-lm")
        registry = registry_models()
        if any(config.LITERT_MODEL.lower() in str(item.get("raw", "")).lower() for item in registry):
            with _AUTO_LOCK:
                _AUTO_STATE.update(status="complete", message="Configured model already appears in the LiteRT-LM registry.", model_id=config.LITERT_MODEL)
            return
        with _AUTO_LOCK:
            _AUTO_STATE.update(status="running", message="Importing the default Qwen3 1.7B model. This may take a while and use about 1 GB of storage and network data.", model_id=config.LITERT_MODEL)
        imported = import_model(MODEL_REPO, MODEL_FILE, config.LITERT_MODEL)
        with _AUTO_LOCK:
            _AUTO_STATE.update(status="complete", message="Model import command completed. Check runtime status before chatting.", model_id=imported)
    except Exception as exc:
        with _AUTO_LOCK:
            _AUTO_STATE.update(status="error", message=str(exc)[:500], model_id=config.LITERT_MODEL)


def start_auto_setup():
    # Treat queued and running as active so rapid clicks cannot launch concurrent imports.
    with _AUTO_LOCK:
        if _AUTO_STATE["status"] in {"queued", "running"}:
            return dict(_AUTO_STATE)
        _AUTO_STATE.update(status="queued", message="Model setup queued.", model_id=config.LITERT_MODEL)
        thread = threading.Thread(target=_auto_setup_worker, name="nano-model-setup", daemon=True)
        thread.start()
        return dict(_AUTO_STATE)
