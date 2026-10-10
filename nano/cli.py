import argparse
import json
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from . import config
from .db import init_db
from .model_manager import info,import_model
from .runtime import status,registry_models

MODEL_REPO="litert-community/Qwen3-4B-Thinking-2507"
MODEL_FILE="Qwen3_4b_thinking_dynamic_wi4b32_afp32.litertlm"

def litert_binary(): return shutil.which("litert-lm") or shutil.which("litert-lm.exe")

def endpoint_responds(url, timeout=1.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError, TimeoutError, ValueError):
        return False


def port_is_open(host, port, timeout=0.35):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def display_host(host):
    return f"[{host}]" if ":" in host and not host.startswith("[") else host


def main():
    p=argparse.ArgumentParser(prog="nano-ai",description="Nano AI local Qwen3 assistant")
    s=p.add_subparsers(dest="cmd")
    for n in ("init","status","model","models","doctor","setup-extras","install-user-service","uninstall-user-service"): s.add_parser(n)
    d=s.add_parser("download-model",aliases=["import-model"]); d.add_argument("--repo",default=MODEL_REPO); d.add_argument("--file",default=MODEL_FILE); d.add_argument("--id",default=None)
    w=s.add_parser("web"); w.add_argument("--host",default=config.HOST); w.add_argument("--port",type=int,default=config.PORT)
    l=s.add_parser("litert-lm"); l.add_argument("--host",default="127.0.0.1"); l.add_argument("--port",type=int,default=9379); l.add_argument("--verbose",action="store_true")
    a=p.parse_args()
    if a.cmd=="init": init_db(); print("Nano initialized")
    elif a.cmd=="status": print(status())
    elif a.cmd=="setup-extras":
        from .setup_extras import setup
        try: print(json.dumps(setup(), indent=2, ensure_ascii=False))
        except (RuntimeError, OSError, subprocess.SubprocessError, ValueError) as e: raise SystemExit(str(e))
    elif a.cmd=="doctor":
        from .doctor import run_checks
        report = run_checks()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        if report["overall"] == "fail": raise SystemExit(1)
    elif a.cmd in {"model","models"}: print(info() if a.cmd=="model" else registry_models())
    elif a.cmd in {"download-model","import-model"}:
        try: print("LiteRT-LM model imported:",import_model(a.repo,a.file,a.id))
        except RuntimeError as e: raise SystemExit(str(e))
    elif a.cmd=="web":
        import os
        if a.host not in {"127.0.0.1","localhost","::1"} and not os.getenv("NANO_API_TOKEN","").strip():
            raise SystemExit("Refusing remote bind without authentication. Set a strong NANO_API_TOKEN first.")
        base=f"http://{display_host(a.host)}:{a.port}"
        if endpoint_responds(base+"/api/system"):
            print(f"Nano AI web server is already responding at {base}; leaving the existing process running.")
            return
        if port_is_open(a.host,a.port):
            raise SystemExit(f"Port {a.port} on {a.host} is already in use by another service. Inspect it with: ss -ltnp 'sport = :{a.port}'")
        import uvicorn
        uvicorn.run("nano.app:app",host=a.host,port=a.port)
    elif a.cmd=="install-user-service":
        from .service import install_user_services
        try: print(json.dumps(install_user_services(), indent=2))
        except (RuntimeError, OSError, subprocess.SubprocessError) as e: raise SystemExit(str(e))
    elif a.cmd=="uninstall-user-service":
        from .service import uninstall_user_services
        try: print(json.dumps(uninstall_user_services(), indent=2))
        except (RuntimeError, OSError, subprocess.SubprocessError) as e: raise SystemExit(str(e))
    elif a.cmd=="litert-lm":
        b=litert_binary()
        if not b: raise SystemExit("litert-lm was not found. Install it with: python -m pip install -U litert-lm")
        base=f"http://{display_host(a.host)}:{a.port}"
        if endpoint_responds(base+"/v1/models"):
            print(f"LiteRT-LM endpoint is already responding at {base}; model service will not be started twice.")
            return
        if port_is_open(a.host,a.port):
            raise SystemExit(f"Port {a.port} on {a.host} is already in use, but LiteRT-LM did not answer at {base}/v1/models. Inspect it with: ss -ltnp 'sport = :{a.port}'")
        cmd=[b,"serve","--host",a.host,"--port",str(a.port)]
        if a.verbose: cmd.append("--verbose")
        subprocess.run(cmd,check=True)
    else: p.print_help()
