import hashlib
import os
from . import config

MODEL_REPO="litert-community/Qwen3-1.7B"
MODEL_FILE="Qwen3-1.7B_dynamic_wi4b32_afp32.litertlm"
MODEL_URL=f"https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}?download=true"

def default_model_path():
    return os.path.join(config.MODEL_DIR,config.MODEL_NAME)

def info():
    p=default_model_path()
    return {"runtime":"litert-lm","name":config.MODEL_NAME,"registry_model":config.LITERT_MODEL,"path":p,"installed":os.path.exists(p),"size":os.path.getsize(p) if os.path.exists(p) else 0,"url":MODEL_URL,"repository":MODEL_REPO}

def sha256(path=None):
    h=hashlib.sha256()
    with open(path or default_model_path(),"rb") as f:
        for c in iter(lambda:f.read(1048576),b""): h.update(c)
    return h.hexdigest()
