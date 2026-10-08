import hashlib,os,urllib.request
from . import config
from .runtime import validate_model_path
MODEL_URL="https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q4_K_M.gguf?download=true"
def default_model_path():return os.path.join(config.MODEL_DIR,config.MODEL_NAME)
def info():
 p=default_model_path()
 return {"name":config.MODEL_NAME,"path":p,"installed":os.path.exists(p),"size":os.path.getsize(p) if os.path.exists(p) else 0,"url":MODEL_URL}
def download(url=MODEL_URL,filename=None):
 p=validate_model_path(os.path.join(config.MODEL_DIR,filename or config.MODEL_NAME));tmp=p+".part"
 urllib.request.urlretrieve(url,tmp);os.replace(tmp,p);return info()
def sha256(path=None):
 h=hashlib.sha256()
 with open(path or default_model_path(),"rb") as f:
  for c in iter(lambda:f.read(1048576),b""):h.update(c)
 return h.hexdigest()
