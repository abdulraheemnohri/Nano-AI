# Model and LiteRT-LM Runtime

Nano AI uses **Qwen3 1.7B** through the official LiteRT-LM CLI. It does not use GGUF or llama.cpp.

## Default artifact

- Repository: `litert-community/Qwen3-1.7B`
- Artifact: `Qwen3-1.7B_dynamic_wi4b32_afp32.litertlm`
- Quantization: dynamic INT4, block-32 weights / FP32 activations
- Context: 4096
- Approximate size: 932–977 MB depending on displayed artifact metadata

The LiteRT-LM registry ID used by Nano is `qwen3-1.7b`.

## Runtime modes

1. **Server mode** — recommended for Nano Web/API. `litert-lm serve --host 127.0.0.1 --port 9379`.
2. **Direct CLI mode** — LiteRT-LM itself supports `litert-lm run` for interactive local inference.

Nano uses server mode because the official server exposes OpenAI-compatible `/v1/models` and `/v1/chat/completions` endpoints.

## Model management

```bash
litert-lm list
litert-lm import --from-huggingface-repo=litert-community/Qwen3-1.7B Qwen3-1.7B_dynamic_wi4b32_afp32.litertlm qwen3-1.7b
```

Nano's `nano-ai download-model` / `import-model` commands call that CLI import operation rather than downloading model bytes itself.

## Configuration

- `NANO_LITERT_URL`
- `NANO_LITERT_MODEL`
- `NANO_LITERT_TIMEOUT`
- `NANO_MAX_CONTEXT`
- `NANO_MODEL_NAME`

LiteRT-LM also has its own `config.json` system for backend and per-model runtime settings. Keep those runtime settings in LiteRT-LM rather than inventing unsupported flags in Nano.
