"""Offline Vosk STT + Piper TTS adapters for Nano AI.

Vosk consumes local mono 16-bit PCM WAV files. Piper is invoked as a fixed
local executable; no network access is used by this module.
"""
import json, subprocess, wave
from functools import lru_cache
from pathlib import Path
try:
    import vosk
except Exception:
    vosk = None
from .config import STT_MODEL, PIPER_COMMAND, PIPER_VOICE

@lru_cache(maxsize=1)
def _vosk_model():
    if vosk is None:
        raise RuntimeError("Vosk is not installed. Install requirements-voice.txt.")
    if not STT_MODEL:
        raise RuntimeError("NANO_STT_MODEL is not configured.")
    model_path = Path(STT_MODEL).expanduser()
    if not model_path.is_dir():
        raise RuntimeError(f"Vosk model directory not found: {model_path}")
    return vosk.Model(str(model_path))

def transcribe_wav(path):
    """Transcribe a local mono 16-bit PCM WAV file with Vosk."""
    with wave.open(str(path), "rb") as wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
            raise ValueError("STT audio must be mono 16-bit WAV.")
        rec = vosk.KaldiRecognizer(_vosk_model(), wf.getframerate())
        parts = []
        while True:
            data = wf.readframes(4000)
            if not data:
                break
            if rec.AcceptWaveform(data):
                parts.append(json.loads(rec.Result()).get("text", ""))
        parts.append(json.loads(rec.FinalResult()).get("text", ""))
    return " ".join(x for x in parts if x).strip()

def speak(text, outfile):
    """Render text to a local WAV file using Piper."""
    if not text or not text.strip():
        raise ValueError("TTS text cannot be empty.")
    output = Path(outfile)
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [PIPER_COMMAND]
    if PIPER_VOICE:
        cmd += ["--model", PIPER_VOICE]
    try:
        with output.open("wb") as out:
            p = subprocess.run(cmd, input=text.encode("utf-8"), stdout=out,
                               stderr=subprocess.PIPE, timeout=60, check=False)
    except FileNotFoundError as e:
        raise RuntimeError(f"Piper executable not found: {PIPER_COMMAND}") from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("Piper timed out after 60 seconds.") from e
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors="ignore") or "Piper failed")
    return output
