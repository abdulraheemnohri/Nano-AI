# Nano AI

Nano AI is a lightweight, privacy-first local talking assistant built around Qwen3 1.7B.

## System

Microphone or text -> local STT -> Qwen3 1.7B -> memory/skills context -> response -> optional Piper TTS.

## Features

- Qwen3 1.7B local inference through llama.cpp.
- FastAPI local web interface.
- SQLite conversation and memory storage.
- Explicit learning for facts and preferences.
- Local knowledge ingestion.
- Search, forget and clear memory.
- Versioned prompt skills with enable/disable and proposals.
- Runtime health and model inventory.
- Local model manager.
- Optional offline Vosk STT and Piper TTS.
- Linux and Windows setup.
- Automated tests and GitHub Actions.
- Dark responsive UI with Talk, Memory, Learning, Skills, Knowledge, Model, Settings and System pages.

## Safety boundary

Nano is intentionally not an agent with external action tools. It does not browse, execute shell commands, control devices, or silently modify neural model weights. Learning means persistent user-visible memory, knowledge and reusable prompt skills.

## Quick start

Install Python 3.10+ and llama.cpp. Then:

1. pip install -e .
2. nano-ai init
3. Place Qwen3-1.7B-Q4_K_M.gguf in models/ or run nano-ai download-model.
4. nano-ai llama
5. In another terminal: nano-ai web
6. Open http://127.0.0.1:8000

Optional voice dependencies are available with the voice extra.

## Configuration

Use environment variables such as NANO_HOST, NANO_PORT, NANO_LLAMA_URL, NANO_MODEL_NAME, NANO_MAX_CONTEXT, NANO_TEMPERATURE, NANO_STT_MODEL and NANO_PIPER_VOICE. See .env.example.

## Documentation

- docs/INSTALL.md
- docs/USER_GUIDE.md
- docs/MODEL.md
- docs/SECURITY.md
- docs/ARCHITECTURE.md
- docs/LEARNING.md

## License

Apache License 2.0.
