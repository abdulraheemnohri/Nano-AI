# Nano AI

Nano AI is a privacy-first, local talking assistant built around **Qwen3 1.7B**.

## Included

- Local Qwen3 1.7B chat through a local llama.cpp-compatible HTTP server.
- Lightweight FastAPI web UI.
- Persistent SQLite conversations and memory.
- Explicit self-learning for facts and preferences taught in conversation.
- Versioned self-skills with proposals and acceptance.
- Urdu/Roman Urdu, reasoning, writing and summarization skills.
- Optional offline speech-to-text with Vosk.
- Optional offline text-to-speech with Piper.
- Windows and Linux setup scripts and automated tests.
- No Firebase, no mandatory cloud service, no external agent/tool execution, and no silent model-weight modification.

## Architecture

Microphone -> STT -> Qwen3 1.7B -> response -> TTS -> speaker

Learning is lightweight: Nano learns memory, knowledge and reusable skill instructions rather than rewriting model weights.

## Quick start

1. Install Python 3.10+.
2. Create a virtual environment and install `requirements.txt`.
3. Install llama.cpp and make `llama-server` available on PATH.
4. Run `python -m nano.cli model` to download Qwen3 1.7B Q4_K_M.
5. Run `python -m nano.cli llama`.
6. In another terminal run `python -m nano.cli web`.
7. Open `http://127.0.0.1:8000`.

For STT install `requirements-voice.txt` and configure `NANO_STT_MODEL`. For Piper, install Piper locally and set `NANO_PIPER_VOICE`.

## Learning

Say `Remember that I prefer Urdu` or `My name is ...`. Nano stores explicit learning candidates in SQLite and supplies active memories to future conversations. Skills are versioned; new skills can be proposed and accepted.

## Security and privacy

Nano binds to localhost by default. It does not expose terminal, browser, filesystem-control or arbitrary external-agent tools.

## Layout

- `nano/app.py` - API and UI
- `nano/model.py` - local model adapter
- `nano/db.py` - SQLite storage
- `nano/learning.py` - learning pipeline
- `nano/skills.py` - skill registry/evolution
- `nano/voice.py` - Vosk/Piper adapters
- `nano/cli.py` - setup/run commands
- `tests/` - automated tests

## License

Apache License 2.0.
