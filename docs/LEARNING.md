# Learning System

Nano's learning is persistent knowledge, not silent model retraining.

## Explicit learning
Supported examples: `Remember that I prefer Urdu`, `My name is ...`, `I prefer ...`, `I like ...`, and `Learn that ...`.

Each memory records kind, confidence, source and timestamps. Duplicate active memories are avoided.

## Knowledge import
The Knowledge page accepts supplied local text and stores sentence-sized knowledge records. Nano does not silently scrape the internet.

## Skill evolution
A proposed skill remains pending until explicitly accepted. Accepting creates or updates a reusable skill; rejecting records the decision.

## Auditability
Learning events are stored in SQLite and exposed in the Learning page/API. Memories can be forgotten individually or cleared.

## Model weights
Nano never silently fine-tunes or changes Qwen3 model weights.


## Conversation feedback loop

After each new answer, use **Helpful** or **Not helpful** and optionally enter a correction or preferred style. Feedback is stored in the local `response_feedback` table and the learning event log. Recent corrections are inserted into later model context as guidance; they do not override the current request or safety policy. Review the Learning page's feedback summary to see totals.

This is retrieval/context adaptation, not fine-tuning. Nano does not silently alter model weights or automatically treat every answer as a fact.

## Autonomous talk

Autonomous talk is opt-in and disabled by default. In Settings, enable `autonomous_talk_enabled`, ensure `voice_enabled` and `auto_tts` are enabled, set the interval (10 minutes to 24 hours), and customize the prompt. While the web UI is open, visible, and idle for at least five minutes, it may ask the local model for a brief check-in and play it through local Piper. It does not speak when the page is hidden or the user is active. It stops when the tab closes and is not a background microphone monitor. Events are logged locally.
