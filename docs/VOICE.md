# Nano AI Voice

Nano AI voice is local/offline: Microphone -> mono 16-bit WAV -> Vosk STT -> Qwen3 4B-Thinking-2507 -> Piper TTS -> speaker.

## Install

`python -m pip install -r requirements-voice.txt` followed by `python -m playwright install chromium` for browser automation. To download default English voice models and browser assets automatically, run `nano-ai setup-extras`. The Qwen3 4B model is about 2.1 GB and can require several GB RAM. followed by `python -m playwright install chromium` for browser automation. To download default English voice models and browser assets automatically, run `nano-ai setup-extras`. The Qwen3 4B model is about 2.1 GB and can require several GB RAM.

## Vosk

Extract a local Vosk speech model under `models/vosk/` and set `NANO_STT_MODEL=models/vosk`. Input must be mono, 16-bit PCM WAV.

## Piper

Install Piper locally or use `piper-tts`. Put a local `.onnx` voice under `models/piper/` and set `NANO_PIPER_COMMAND=piper` and `NANO_PIPER_VOICE=models/piper/<voice>.onnx`.

## API

`POST /api/voice/stt` accepts a WAV upload and returns `{\"text\":\"...\"}`.

`GET /api/voice/tts?text=...` returns a WAV audio response.

## Privacy

No cloud STT/TTS is required and Nano does not use browser SpeechRecognition. Audio remains on the machine running Nano.


## Autonomous check-ins

The Talk page can speak proactive check-ins while the tab is open, visible, and idle. Enable **Autonomous talk** in Settings and configure the interval and prompt. This is off by default, requires the local model and Piper voice, and never requires cloud speech services. The browser does not continue speaking after the tab is closed.
