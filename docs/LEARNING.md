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
