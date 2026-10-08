"""Offline Vosk STT and Piper TTS adapters."""
import json, subprocess, wave
from functools import lru_cache
from pathlib import Path
try:
    import vosk
except Exception:
    vosk=None
from .config import STT_MODEL,PIPER_COMMAND,PIPER_VOICE
@lru_cache(maxsize=1)
def _vosk_model():
    if vosk is None: raise RuntimeError("Vosk is not installed. Run: python -m pip install -r requirements-voice.txt")
    model=Path(STT_MODEL).expanduser()
    if not model.is_dir(): raise RuntimeError(f"Vosk model directory not found: {model}")
    return vosk.Model(str(model))
def transcribe_wav(path):
    with wave.open(str(path),"rb") as wf:
        if wf.getnchannels()!=1 or wf.getsampwidth()!=2: raise ValueError("STT audio must be mono 16-bit PCM WAV.")
        rec=vosk.KaldiRecognizer(_vosk_model(),wf.getframerate()); parts=[]
        while True:
            data=wf.readframes(4000)
            if not data: break
            if rec.AcceptWaveform(data): parts.append(json.loads(rec.Result()).get("text",""))
        parts.append(json.loads(rec.FinalResult()).get("text",""))
    return " ".join(x for x in parts if x).strip()
def speak(text,outfile):
    if not text or not text.strip(): raise ValueError("TTS text cannot be empty.")
    out=Path(outfile); out.parent.mkdir(parents=True,exist_ok=True)
    cmd=[PIPER_COMMAND]+(["--model",PIPER_VOICE] if PIPER_VOICE else [])
    try:
        with out.open("wb") as fp: p=subprocess.run(cmd,input=text.encode("utf-8"),stdout=fp,stderr=subprocess.PIPE,timeout=60,check=False)
    except FileNotFoundError as e: raise RuntimeError(f"Piper executable not found: {PIPER_COMMAND}") from e
    except subprocess.TimeoutExpired as e: raise RuntimeError("Piper timed out after 60 seconds.") from e
    if p.returncode: raise RuntimeError(p.stderr.decode(errors="ignore") or "Piper failed")
    return out
