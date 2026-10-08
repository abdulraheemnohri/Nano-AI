import json
import os
import shutil
import subprocess
import urllib.request
from . import config

def litert_lm_binary():
    return shutil.which("litert-lm") or shutil.which("litert-lm.exe")

def registry_models():
    binary = litert_lm_binary()
    if not binary:
        return []
    try:
        p = subprocess.run([binary, "list"], capture_output=True, text=True, timeout=20, check=False)
        if p.returncode != 0:
            return []
        return [{"raw": line.strip()} for line in p.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.TimeoutExpired):
        return []

def status():
    r = {"runtime":"litert-lm","configured_url":config.LITERT_URL,"model":config.LITERT_MODEL,
         "reachable":False,"binary":bool(litert_lm_binary()),"models":[],"registry":[]}
    r["registry"] = registry_models()
    try:
        with urllib.request.urlopen(config.LITERT_URL.rstrip("/") + "/v1/models", timeout=1.5) as x:
            r["reachable"] = x.status == 200
            if x.status == 200:
                data = json.loads(x.read().decode("utf-8"))
                r["models"] = [m.get("id") for m in data.get("data", [])]
    except Exception:
        pass
    return r

def installed_models():
    out = []
    for root, _, names in os.walk(config.MODEL_DIR):
        for n in names:
            if n.lower().endswith(".litertlm"):
                p = os.path.join(root, n)
                out.append({"name":n,"path":p,"size":os.path.getsize(p)})
    return sorted(out, key=lambda x:x["name"].lower())

def validate_model_path(path):
    path=os.path.abspath(path); base=os.path.abspath(config.MODEL_DIR)
    if os.path.commonpath([path,base]) != base:
        raise ValueError("Model path must stay inside model directory")
    return path
