import hashlib
import shutil
import subprocess
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
