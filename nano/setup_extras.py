"""Opt-in installer for offline voice assets and Playwright Chromium."""
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from . import config

VOSK_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"
VOSK_DIR = config.MODEL_DIR / "vosk-model-small-en-us-0.15"
PIPER_DIR = config.MODEL_DIR / "piper"
PIPER_MODEL = PIPER_DIR / "en_US-lessac-medium.onnx"
PIPER_CONFIG = PIPER_DIR / "en_US-lessac-medium.onnx.json"


def _download(url, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "Nano-AI-optional-setup"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        if not temporary.is_file() or temporary.stat().st_size < 1024:
            raise RuntimeError(f"Download appears incomplete: {url}")
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _install_python_extras():
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", ".[voice,browser]"],
        cwd=str(config.ROOT), check=True,
    )


def _install_chromium():
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)


def _install_vosk_model():
    if (VOSK_DIR / "am" / "final.mdl").is_file():
        return "already-installed"
    archive = config.MODEL_DIR / "vosk-model-small-en-us-0.15.zip"
    staging = config.MODEL_DIR / ".vosk-extract"
    _download(VOSK_URL, archive)
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(archive) as zipped:
            root = staging.resolve()
            for item in zipped.infolist():
                target = (staging / item.filename).resolve()
                if target != root and root not in target.parents:
                    raise RuntimeError("Vosk archive contains an unsafe path; refusing to extract it.")
            zipped.extractall(staging)
        candidates = list(staging.glob("**/am/final.mdl"))
        if not candidates:
            raise RuntimeError("Downloaded Vosk archive did not contain the expected acoustic model.")
        model_root = candidates[0].parent.parent
        shutil.rmtree(VOSK_DIR, ignore_errors=True)
        shutil.move(str(model_root), str(VOSK_DIR))
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        archive.unlink(missing_ok=True)
    return "downloaded"


def _install_piper_voice():
    PIPER_DIR.mkdir(parents=True, exist_ok=True)
    if not PIPER_MODEL.is_file():
        _download(f"{PIPER_BASE}/en_US-lessac-medium.onnx?download=true", PIPER_MODEL)
    if not PIPER_CONFIG.is_file():
        _download(f"{PIPER_BASE}/en_US-lessac-medium.onnx.json?download=true", PIPER_CONFIG)
    return "already-installed" if PIPER_MODEL.exists() and PIPER_CONFIG.exists() else "downloaded"


def setup():
    """Install optional dependencies and download default local voice/browser assets."""
    _install_python_extras()
    _install_chromium()
    vosk_state = _install_vosk_model()
    _install_piper_voice()
    return {
        "ok": True,
        "voice_stt": str(VOSK_DIR),
        "voice_tts": str(PIPER_MODEL),
        "browser": "Playwright Chromium installed",
        "vosk_model": vosk_state,
        "offline_after_setup": True,
        "note": "Default speech assets are English (US); setup does not enable desktop control or approve browser actions.",
    }
