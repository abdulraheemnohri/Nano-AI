# Nano AI

Nano AI is a lightweight, privacy-first local talking assistant built around **Qwen3 1.7B**.

## Voice

Nano supports optional offline voice:
- **Vosk**: local speech-to-text.
- **Piper**: local text-to-speech.
- Web UI voice controls.
- WAV upload/recording workflow.
- Local WAV playback.
- No cloud speech API.

Voice is optional; text chat works without Vosk/Piper.

## Quick start

1. Install Python 3.10+ and llama.cpp.
2. `pip install -e .`
3. `nano-ai init`
4. Place Qwen3-1.7B-Q4_K_M.gguf in `models/` or run `nano-ai download-model`.
5. `nano-ai llama`
6. In another terminal: `nano-ai web`
7. Open `http://127.0.0.1:8000`

For voice, follow **docs/VOICE.md** and install `pip install -e ".[voice]"`.

## Safety boundary

Nano is intentionally not an agent with external action tools. It does not browse, execute shell commands, control devices, or silently modify model weights. Learning means persistent user-visible memory, knowledge and reusable prompt skills.

## Docs

- docs/INSTALL.md
- docs/VOICE.md
- docs/USER_GUIDE.md
- docs/MODEL.md
- docs/SECURITY.md
- docs/ARCHITECTURE.md
- docs/LEARNING.md
