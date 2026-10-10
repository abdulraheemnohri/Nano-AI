"""Load Nano AI's standalone web UI assets."""
from pathlib import Path

_STATIC = Path(__file__).with_name("static")
HTML = (_STATIC / "index.html").read_text(encoding="utf-8")
CSS = (_STATIC / "app.css").read_text(encoding="utf-8")
JS = (_STATIC / "app.js").read_text(encoding="utf-8")
