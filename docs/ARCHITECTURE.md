# Nano AI Architecture

Nano is deliberately a small local assistant.

## Layers

1. **Voice layer** — browser speech input or Vosk WAV transcription; Piper provides optional offline speech.
2. **Conversation layer** — FastAPI receives text and manages SQLite history.
3. **Brain layer** — Qwen3 1.7B is served by a local llama.cpp-compatible endpoint.
4. **Memory layer** — SQLite stores conversations, durable memories and learning events.
5. **Skill layer** — versioned skill prompts provide reusable behavior.
6. **Knowledge layer** — explicit local knowledge import stores text as searchable memory.

Nano has no terminal executor, browser agent, device-control agent or arbitrary plugin execution. Self-learning is constrained to data and skill evolution, so it cannot silently alter model weights or execute new capabilities.
