# Voice installation

Nano voice is local/offline: **Vosk** performs speech-to-text and **Piper** performs text-to-speech.

## 1. Python voice dependencies

Linux/Windows:
```bash
python -m pip install -e ".[voice]"
```

## 2. Vosk

Download a Vosk model from the official Vosk model releases and extract it locally, for example:

```
models/vosk/
```

Then set:
```
NANO_STT_MODEL=models/vosk
```

The API accepts **mono, 16-bit PCM WAV**. This avoids requiring ffmpeg or a cloud transcription service.

## 3. Piper

Install the Piper executable for your platform and download a compatible local voice model. Set:

```
NANO_PIPER_COMMAND=piper
NANO_PIPER_VOICE=models/piper/en_US-lessac-medium.onnx
```

If Piper is not on PATH, set NANO_PIPER_COMMAND to its full local executable path.

## 4. Voice flow

WAV microphone/file -> Vosk -> text -> Qwen3 1.7B -> response -> Piper -> WAV speaker playback.

No audio is uploaded to a remote service. Nano does not use browser speech recognition because that can depend on a remote browser provider.
