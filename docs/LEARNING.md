# Learning System

Nano's learning is persistent knowledge, not silent model retraining.

## Explicit learning

Supported examples include:

- `Remember that I prefer Urdu`
- `My name is ...`
- `I prefer ...`
- `I like ...`
- `Learn that ...`

Each extracted memory records kind, confidence, source and timestamps. Duplicate active memories are not created.

## Knowledge import

The Knowledge page accepts supplied local text and stores sentence-sized knowledge records. This is deliberately user-provided/local input; Nano does not silently scrape the internet.

## Skill evolution

A skill proposal contains a name, description and prompt. It remains pending until explicitly accepted. Accepting creates or updates a reusable skill; rejecting records the decision.

## Auditability

Learning events are stored in SQLite and exposed in the Learning page/API. Memory can be individually forgotten or cleared.

## Model weights

Nano never silently fine-tunes or changes Qwen3 model weights.
