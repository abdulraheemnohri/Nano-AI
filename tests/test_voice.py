import wave
from pathlib import Path
from unittest.mock import patch
import pytest
import nano.voice as voice

def make_wav(path: Path, channels=1):
    with wave.open(str(path),"wb") as wf:
        wf.setnchannels(channels); wf.setsampwidth(2); wf.setframerate(16000); wf.writeframes(b"\0\0"*160)

def test_voice_status_shape():
    s=voice.voice_status()
    assert s["stt"]["engine"]=="vosk" and s["stt"]["offline"]
    assert s["tts"]["engine"]=="piper" and s["tts"]["offline"]

def test_stereo_rejected(tmp_path):
    p=tmp_path/"x.wav"; make_wav(p,2)
    if voice.vosk is None:
        with pytest.raises(RuntimeError): voice.transcribe_wav(p)
    else:
        with pytest.raises(ValueError,match="mono"): voice.transcribe_wav(p)

def test_empty_tts_rejected(tmp_path):
    with pytest.raises(ValueError): voice.speak("",tmp_path/"x.wav")

def test_piper_is_local_subprocess(tmp_path):
    out=tmp_path/"x.wav"
    result=type("R",(),{"returncode":0,"stderr":b""})()
    with patch("nano.voice.subprocess.run",return_value=result) as run:
        voice.speak("hello",out)
    assert out.exists()
    run.assert_called_once()
    assert run.call_args.kwargs["input"]==b"hello"
