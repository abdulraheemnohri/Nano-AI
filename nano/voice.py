import subprocess, tempfile, wave
from pathlib import Path
try:
    import vosk
except Exception:
    vosk=None
from .config import STT_MODEL,PIPER_COMMAND,PIPER_VOICE

def transcribe_wav(path):
    if not vosk: raise RuntimeError('Vosk is not installed. Install requirements-voice.txt.')
    if not STT_MODEL: raise RuntimeError('NANO_STT_MODEL is not configured.')
    model=vosk.Model(STT_MODEL)
    with wave.open(str(path),'rb') as wf:
        if wf.getnchannels()!=1 or wf.getsampwidth()!=2: raise ValueError('STT audio must be mono 16-bit WAV.')
        rec=vosk.KaldiRecognizer(model,wf.getframerate()); parts=[]
        while True:
            data=wf.readframes(4000)
            if not data: break
            if rec.AcceptWaveform(data):
                import json; parts.append(json.loads(rec.Result()).get('text',''))
        import json; parts.append(json.loads(rec.FinalResult()).get('text',''))
    return ' '.join(x for x in parts if x).strip()

def speak(text,outfile):
    cmd=[PIPER_COMMAND]
    if PIPER_VOICE: cmd += ['--model',PIPER_VOICE]
    with open(outfile,'wb') as out:
        p=subprocess.run(cmd,input=text.encode('utf-8'),stdout=out,stderr=subprocess.PIPE,timeout=60)
    if p.returncode: raise RuntimeError(p.stderr.decode(errors='ignore') or 'Piper failed')
    return outfile
