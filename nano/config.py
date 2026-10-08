import os
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
DATA_DIR=Path(os.getenv('NANO_DATA_DIR',ROOT/'data')).resolve()
MODEL_DIR=Path(os.getenv('NANO_MODEL_DIR',ROOT/'models')).resolve()
SKILLS_DIR=Path(os.getenv('NANO_SKILLS_DIR',ROOT/'skills')).resolve()
DB_PATH=Path(os.getenv('NANO_DB',DATA_DIR/'nano.sqlite3')).resolve()
HOST=os.getenv('NANO_HOST','127.0.0.1')
PORT=int(os.getenv('NANO_PORT','8000'))
LLAMA_URL=os.getenv('NANO_LLAMA_URL','http://127.0.0.1:8080')
LLAMA_MODEL=os.getenv('NANO_MODEL_NAME','Qwen3-1.7B-Q4_K_M.gguf')
MAX_CONTEXT=int(os.getenv('NANO_MAX_CONTEXT','4096'))
TEMPERATURE=float(os.getenv('NANO_TEMPERATURE','0.7'))
STT_MODEL=os.getenv('NANO_STT_MODEL','')
PIPER_COMMAND=os.getenv('NANO_PIPER_COMMAND','piper')
PIPER_VOICE=os.getenv('NANO_PIPER_VOICE','')
for p in (DATA_DIR,MODEL_DIR,SKILLS_DIR): p.mkdir(parents=True,exist_ok=True)
