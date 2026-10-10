# Nano AI Architecture

Nano is a lightweight local-first assistant with explicit learning and reusable skills. It intentionally does not contain arbitrary agent tools.

## Layers
1. Web/API — FastAPI, local HTML/JS UI and health endpoints.
2. Voice — optional local Vosk STT and Piper TTS.
3. Conversation — SQLite conversation/message persistence.
4. Brain — Qwen3 4B-Thinking-2507 through LiteRT-LM's local OpenAI-compatible server.
5. Memory — searchable SQLite memories with confidence/source/audit state.
6. Learning — explicit learning phrases, local knowledge import and auditable events.
7. Skills — built-in prompts plus proposed skills requiring explicit acceptance.
8. Model management — LiteRT-LM registry inspection/import.
9. Settings — validated persistent runtime settings.

## Request flow
`UI -> /api/chat -> core.respond -> memory/skills context -> LiteRT-LM -> SQLite -> UI`

Nano cannot browse, execute shell commands, control devices, invoke arbitrary plugins or silently modify model weights.
