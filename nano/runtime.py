import os,shutil,urllib.request
from . import config
def llama_server_binary(): return shutil.which("llama-server") or shutil.which("llama-server.exe")
def status():
 r={"configured_url":config.LLAMA_URL,"reachable":False,"binary":bool(llama_server_binary())}
 try:
  with urllib.request.urlopen(config.LLAMA_URL.rstrip("/")+"/health",timeout=1.5) as x:r["reachable"]=200<=x.status<500
 except Exception:pass
 return r
def installed_models():
 out=[]
 for root,_,names in os.walk(config.MODEL_DIR):
  for n in names:
   if n.lower().endswith((".gguf",".litertlm",".onnx",".safetensors")):
    p=os.path.join(root,n);out.append({"name":n,"path":p,"size":os.path.getsize(p)})
 return sorted(out,key=lambda x:x["name"].lower())
def validate_model_path(path):
 path=os.path.abspath(path);base=os.path.abspath(config.MODEL_DIR)
 if os.path.commonpath([path,base])!=base:raise ValueError("Model path must stay inside model directory")
 return path
