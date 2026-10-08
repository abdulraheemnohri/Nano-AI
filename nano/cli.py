import argparse
import shutil
import subprocess
from . import config
from .db import init_db
from .model_manager import info,import_model
from .runtime import status,registry_models

MODEL_REPO="litert-community/Qwen3-1.7B"
MODEL_FILE="Qwen3-1.7B_dynamic_wi4b32_afp32.litertlm"

def litert_binary(): return shutil.which("litert-lm") or shutil.which("litert-lm.exe")

def main():
    p=argparse.ArgumentParser(prog="nano-ai",description="Nano AI local Qwen3 assistant")
    s=p.add_subparsers(dest="cmd")
    for n in ("init","status","model","models"): s.add_parser(n)
    d=s.add_parser("download-model",aliases=["import-model"]); d.add_argument("--repo",default=MODEL_REPO); d.add_argument("--file",default=MODEL_FILE); d.add_argument("--id",default=None)
    w=s.add_parser("web"); w.add_argument("--host",default=config.HOST); w.add_argument("--port",type=int,default=config.PORT)
    l=s.add_parser("litert-lm"); l.add_argument("--host",default="127.0.0.1"); l.add_argument("--port",type=int,default=9379); l.add_argument("--verbose",action="store_true")
    a=p.parse_args()
    if a.cmd=="init": init_db(); print("Nano initialized")
    elif a.cmd=="status": print(status())
    elif a.cmd in {"model","models"}: print(info() if a.cmd=="model" else registry_models())
    elif a.cmd in {"download-model","import-model"}:
        try: print("LiteRT-LM model imported:",import_model(a.repo,a.file,a.id))
        except RuntimeError as e: raise SystemExit(str(e))
    elif a.cmd=="web":
        import uvicorn; uvicorn.run("nano.app:app",host=a.host,port=a.port)
    elif a.cmd=="litert-lm":
        b=litert_binary()
        if not b: raise SystemExit("litert-lm was not found. Install it with: python -m pip install -U litert-lm")
        cmd=[b,"serve","--host",a.host,"--port",str(a.port)]
        if a.verbose: cmd.append("--verbose")
        subprocess.run(cmd,check=True)
    else: p.print_help()
