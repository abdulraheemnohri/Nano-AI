# Nano AI Architecture

Nano is a lightweight, local-first assistant with explicit learning and reusable skills. It intentionally does **not** contain arbitrary agent tools.

## Layers

1. **Web/API layer** — FastAPI, local HTML/JS UI, conversation APIs and health endpoints.
2. **Voice layer** — optional local Vosk STT and Piper TTS.
3. **Conversation layer** — SQLite conversation/message persistence.
4. **Brain layer** — Qwen3 1.7B through LiteRT-LM's OpenAI-compatible local server.
5. **Memory layer** — searchable SQLite durable memories with source, confidence and deletion state.
6. **Learning layer** — explicit learning phrases, knowledge import and auditable learning events.
7. **Skill layer** — built-in prompts plus proposed skills that require explicit acceptance.
8. **Model management layer** — LiteRT-LM registry inspection/import, without inventing registry deletion commands.
9. **Settings layer** — persistent user settings with validation and runtime use.

## Request flow

`UI -> /api/chat -> core.respond -> memory/skills context -> LiteRT-LM -> SQLite -> UI`

The model receives only supplied local context. It cannot browse, execute shell commands, control devices, invoke arbitrary plugins, or silently modify model weights.

## Security

Bind both Nano and LiteRT-LM to localhost by default. If exposing them to a network, add authentication, TLS and network controls outside this project.
