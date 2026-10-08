import argparse,subprocess,sys,urllib.request
from pathlib import Path
from .config import MODEL_DIR,HOST,PORT,LLAMA_MODEL
from .db import init_db

def download_model():
 url='https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q4_K_M.gguf?download=true'
 dst=MODEL_DIR/LLAMA_MODEL
 if dst.exists(): print(dst); return
 print('Downloading Qwen3 1.7B Q4_K_M...')
 urllib.request.urlretrieve(url,dst); print(dst)

def main():
 p=argparse.ArgumentParser(prog='nano-ai'); sub=p.add_subparsers(dest='cmd')
 sub.add_parser('init'); sub.add_parser('model')
 q=sub.add_parser('llama'); q.add_argument('--binary',default='llama-server')
 sub.add_parser('web')
 a=p.parse_args()
 if a.cmd=='init': init_db(); print('Nano AI initialized')
 elif a.cmd=='model': download_model()
 elif a.cmd=='llama':
  model=MODEL_DIR/LLAMA_MODEL
  if not model.exists(): download_model()
  subprocess.run([a.binary,'-m',str(model),'--host','127.0.0.1','--port','8080','-c','4096'])
 elif a.cmd=='web':
  subprocess.run([sys.executable,'-m','uvicorn','nano.app:app','--host',HOST,'--port',str(PORT)])
 else: p.print_help()
if __name__=='__main__': main()
