"""Restricted terminal actions. Never invokes a shell or accepts arbitrary commands."""
import os
import subprocess
from pathlib import Path
from . import config

WORKSPACE = Path(os.getenv("NANO_WORKSPACE", str(config.ROOT))).expanduser().resolve()
MAX_OUTPUT = 12000

def _safe_path(value):
    raw = str(value or ".")
    if "\x00" in raw or Path(raw).is_absolute() or any(p == ".." for p in Path(raw).parts):
        raise ValueError("Paths must be relative to the configured workspace and cannot traverse upward.")
    target = (WORKSPACE / raw).resolve()
    if target != WORKSPACE and WORKSPACE not in target.parents:
        raise ValueError("Path escapes the configured workspace.")
    return target

def run_command(name, args=None, timeout=15):
    args = args or []
    if not isinstance(args,list) or len(args)>10 or any(not isinstance(x,str) or len(x)>300 for x in args):
        raise ValueError("args must be a list of at most 10 short strings.")
    if isinstance(timeout,bool) or not isinstance(timeout,int) or not 1 <= timeout <= 30:
        raise ValueError("timeout must be between 1 and 30 seconds.")
    cwd = WORKSPACE
    if name in {"pwd","python-version","pip-version"} and not args:
        argv = {"pwd":["pwd"],"python-version":[os.sys.executable,"--version"],"pip-version":[os.sys.executable,"-m","pip","--version"]}[name]
    elif name == "ls" and len(args)<=1:
        target = _safe_path(args[0] if args else ".")
        argv = ["ls","-la",str(target)]
    elif name == "git-status" and not args:
        argv = ["git","status","--short","--branch"]
    elif name == "git-log" and not args:
        argv = ["git","log","-5","--oneline"]
    elif name == "git-diff" and not args:
        argv = ["git","diff","--stat"]
    elif name == "pytest" and args in ([],["-q"]):
        argv = [os.sys.executable,"-m","pytest","-q"]
    else:
        raise ValueError("Command is not allowlisted. Allowed: pwd, ls [relative-path], git-status, git-log, git-diff, python-version, pip-version, pytest [-q].")
    try:
        proc = subprocess.run(argv,cwd=str(cwd),capture_output=True,text=True,timeout=timeout,
                              shell=False,check=False)
    except subprocess.TimeoutExpired:
        return {"command":name,"status":"timeout","returncode":None,"stdout":"","stderr":f"Command exceeded {timeout} seconds."}
    return {"command":name,"status":"complete" if proc.returncode==0 else "error",
            "returncode":proc.returncode,"stdout":proc.stdout[-MAX_OUTPUT:],"stderr":proc.stderr[-MAX_OUTPUT:]}
