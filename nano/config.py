import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("NANO_DATA_DIR", ROOT / "data")).expanduser().resolve()
MODEL_DIR = Path(os.getenv("NANO_MODEL_DIR", ROOT / "models")).expanduser().resolve()
SKILLS_DIR = Path(os.getenv("NANO_SKILLS_DIR", ROOT / "skills")).expanduser().resolve()
DB_PATH = Path(os.getenv("NANO_DB", DATA_DIR / "nano.sqlite3")).expanduser().resolve()
HOST = os.getenv("NANO_HOST", "127.0.0.1")
PORT = int(os.getenv("NANO_PORT", "8000"))
LITERT_URL = os.getenv("NANO_LITERT_URL", "http://127.0.0.1:9379")
LITERT_MODEL = os.getenv("NANO_LITERT_MODEL", "qwen3-4b-thinking-2507")
MODEL_NAME = os.getenv("NANO_MODEL_NAME", "Qwen3_4b_thinking_dynamic_wi4b32_afp32.litertlm")
MAX_CONTEXT = int(os.getenv("NANO_MAX_CONTEXT", "4096"))
TEMPERATURE = float(os.getenv("NANO_TEMPERATURE", "0.7"))
LITERT_TIMEOUT = int(os.getenv("NANO_LITERT_TIMEOUT", "180"))
MAX_MESSAGE_CHARS = int(os.getenv("NANO_MAX_MESSAGE_CHARS", "12000"))
LEARNING_ENABLED = os.getenv("NANO_LEARNING_ENABLED", "true").lower() not in {"0", "false", "no", "off"}
STT_MODEL = os.getenv("NANO_STT_MODEL", str(MODEL_DIR / "vosk-model-small-en-us-0.15"))
PIPER_COMMAND = os.getenv("NANO_PIPER_COMMAND", "piper")
PIPER_VOICE = os.getenv("NANO_PIPER_VOICE", str(MODEL_DIR / "piper" / "en_US-lessac-medium.onnx"))

for directory in (DATA_DIR, MODEL_DIR, SKILLS_DIR):
    directory.mkdir(parents=True, exist_ok=True)
