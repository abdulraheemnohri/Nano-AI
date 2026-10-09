import json
import os
import shutil
import subprocess
import urllib.error
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
         "reachable":False,"binary":bool(litert_lm_binary()),"models":[],"registry":[],"endpoint_error":None}
    r["registry"] = registry_models()
    try:
        with urllib.request.urlopen(config.LITERT_URL.rstrip("/") + "/v1/models", timeout=1.5) as x:
            r["reachable"] = x.status == 200
            if x.status == 200:
                data = json.loads(x.read().decode("utf-8"))
                r["models"] = [m.get("id") for m in data.get("data", [])]
    except urllib.error.HTTPError as exc:
        r["endpoint_error"] = f"HTTP {exc.code}"
    except urllib.error.URLError as exc:
        r["endpoint_error"] = str(getattr(exc, "reason", exc))[:120]
    except Exception as exc:
        r["endpoint_error"] = f"{type(exc).__name__}: {exc}"[:120]
    return r

def _serves_model(served, model):
    return any(
        str(item).strip().lower() == str(model).strip().lower()
        for item in served
        if item is not None
    )

def model_readiness(runtime):
    """Classify model readiness with honest, actionable diagnostics.

    Returns a dict with a check status, a human-readable detail, and a
    model_loaded flag (False when the model is not served, True when it is,
    and None when the served-model list is unknown).
    """
    url = runtime.get("configured_url", config.LITERT_URL)
    model = runtime.get("model", config.LITERT_MODEL)
    if not runtime.get("reachable"):
        if runtime.get("binary"):
            hint = "Start the LiteRT-LM server with: nano-ai litert-lm"
        else:
            hint = "Install LiteRT-LM first (python -m pip install -U litert-lm), then start it with: nano-ai litert-lm"
        detail = f"Model endpoint is not reachable at {url}. {hint}."
        error = runtime.get("endpoint_error")
        if error:
            detail += f" Endpoint error: {error}."
        return {"status": "warn", "detail": detail, "model_loaded": False}
    served = runtime.get("models")
    if isinstance(served, list):
        if _serves_model(served, model):
            return {
                "status": "ok",
                "detail": f"Model endpoint is reachable at {url} and the configured model {model} is served.",
                "model_loaded": True,
            }
        if served:
            listed = ", ".join(str(item) for item in served[:10])
            return {
                "status": "warn",
                "detail": (
                    f"Model endpoint is reachable at {url}, but the configured model {model} is not served "
                    f"(served models: {listed}). Import it with: nano-ai download-model, or point "
                    "NANO_LITERT_MODEL at a served model."
                ),
                "model_loaded": False,
            }
        return {
            "status": "warn",
            "detail": (
                f"Model endpoint is reachable at {url}, but it serves no models. "
                "Import one with: nano-ai download-model, then verify with: nano-ai status."
            ),
            "model_loaded": False,
        }
    return {"status": "ok", "detail": f"Model endpoint is reachable at {url}.", "model_loaded": None}

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
