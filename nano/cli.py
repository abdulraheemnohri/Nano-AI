import argparse
import shutil
import subprocess
from . import config
from .db import init_db
from .model_manager import info
from .runtime import status

MODEL_REPO="litert-community/Qwen3-1.7B"
MODEL_FILE="Qwen3-1.7B_dynamic_wi4b32_afp32.litertlm"

def litert_binary():
    return shutil.which("litert-lm") or shutil.which("litert-lm.exe")

def main():
    p=argparse.ArgumentParser(prog="nano-ai")
    s=p.add_subparsers(dest="cmd")
    for n in ("init","status","model"): s.add_parser(n)
    d=s.add_parser("download-model"); d.add_argument("--repo",default=MODEL_REPO); d.add_argument("--file",default=MODEL_FILE)
    w=s.add_parser("web"); w.add_argument("--host",default=config.HOST); w.add_argument("--port",type=int,default=config.PORT)
    l=s.add_parser("litert-lm"); l.add_argument("--host",default="127.0.0.1"); l.add_argument("--port",type=int,default=9379)
    a=p.parse_args()
    if a.cmd=="init":
        init_db(); print("Nano initialized")
    elif a.cmd=="status":
        print(status())
    elif a.cmd=="model":
        print(info())
    elif a.cmd=="download-model":
        b=litert_binary()
        if not b: raise SystemExit("litert-lm was not found. Install it with: python -m pip install -U litert-lm")
        subprocess.run([b,"import",f"--from-huggingface-repo={a.repo}",a.file,config.LITERT_MODEL],check=True)
        print("LiteRT-LM model imported:",config.LITERT_MODEL)
    elif a.cmd=="web":
        import uvicorn; uvicorn.run("nano.app:app",host=a.host,port=a.port)
    elif a.cmd=="litert-lm":
        b=litert_binary()
        if not b: raise SystemExit("litert-lm was not found. Install it with: python -m pip install -U litert-lm")
        subprocess.run([b,"serve","--host",a.host,"--port",str(a.port)],check=True)
    else:
        p.print_help()
