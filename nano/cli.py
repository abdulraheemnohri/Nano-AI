import argparse,subprocess,shutil
from . import config
from .db import init_db
from .model_manager import download,info,default_model_path
from .runtime import status

def main():
 p=argparse.ArgumentParser(prog="nano-ai")
 s=p.add_subparsers(dest="cmd")
 for n in ("init","status","model","download-model"):s.add_parser(n)
 w=s.add_parser("web");w.add_argument("--host",default=config.HOST);w.add_argument("--port",type=int,default=config.PORT)
 l=s.add_parser("llama");l.add_argument("--port",type=int,default=8080)
 a=p.parse_args()
 if a.cmd=="init":init_db();print("Nano initialized")
 elif a.cmd=="status":print(status())
 elif a.cmd=="model":print(info())
 elif a.cmd=="download-model":print(download())
 elif a.cmd=="web":
  import uvicorn;uvicorn.run("nano.app:app",host=a.host,port=a.port)
 elif a.cmd=="llama":
  b=shutil.which("llama-server") or shutil.which("llama-server.exe")
  if not b:raise SystemExit("llama-server was not found on PATH")
  subprocess.run([b,"-m",default_model_path(),"--host","127.0.0.1","--port",str(a.port),"--ctx-size",str(config.MAX_CONTEXT)],check=True)
 else:p.print_help()
