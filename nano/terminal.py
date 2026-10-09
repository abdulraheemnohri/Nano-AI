"""Restricted, cross-platform terminal actions. Never invokes a shell or accepts arbitrary commands."""
import os
import subprocess
import sys
from pathlib import Path
from . import config

WORKSPACE = Path(os.getenv("NANO_WORKSPACE", str(config.ROOT))).expanduser().resolve()
MAX_OUTPUT = 12000

def _safe_path(value):
    raw = str(value or ".")
    if "\\x00" in raw or Path(raw).is_absolute() or any(p == ".." for p in Path(raw).parts):
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
    if name == "pwd" and not args:
        return {"command":name,"status":"complete","returncode":0,"stdout":str(WORKSPACE),"stderr":""}
    if name == "ls" and len(args)<=1:
        target = _safe_path(args[0] if args else ".")
        if not target.exists() or not target.is_dir():
            raise ValueError("The selected path is not an existing directory.")
        entries=[]
        for item in sorted(target.iterdir(),key=lambda p:p.name.lower())[:500]:
            try: size=item.stat().st_size if item.is_file() else 0
            except OSError: size=0
            entries.append(("d " if item.is_dir() else "f ")+item.name+(f" ({size} bytes)" if item.is_file() else ""))
        return {"command":name,"status":"complete","returncode":0,"stdout":"\\n".join(entries),"stderr":""}
    commands = {
        "git-status": ["git","status","--short","--branch"],
        "git-log": ["git","log","-5","--oneline"],
        "git-diff": ["git","diff","--stat"],
        "python-version": [sys.executable,"--version"],
        "pip-version": [sys.executable,"-m","pip","--version"],
    }
    if name == "pytest" and args in ([],["-q"]):
        argv=[sys.executable,"-m","pytest","-q"]
    elif name in commands and not args:
        argv=commands[name]
    else:
        raise ValueError("Command is not allowlisted. Allowed: pwd, ls [relative-path], git-status, git-log, git-diff, python-version, pip-version, pytest [-q].")
    try:
        proc = subprocess.run(argv,cwd=str(WORKSPACE),capture_output=True,text=True,timeout=timeout,
                              shell=False,check=False)
    except FileNotFoundError as exc:
        return {"command":name,"status":"error","returncode":127,"stdout":"","stderr":f"Required executable not found: {argv[0]}"}
    except subprocess.TimeoutExpired:
        return {"command":name,"status":"timeout","returncode":None,"stdout":"","stderr":f"Command exceeded {timeout} seconds."}
    return {"command":name,"status":"complete" if proc.returncode==0 else "error",
            "returncode":proc.returncode,"stdout":proc.stdout[-MAX_OUTPUT:],"stderr":proc.stderr[-MAX_OUTPUT:]}
