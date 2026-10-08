# Model and LiteRT-LM Runtime

Nano AI uses Qwen3 1.7B through the official LiteRT-LM CLI. It does not use GGUF or llama.cpp.

## Default artifact
- Repository: `litert-community/Qwen3-1.7B`
- Artifact: `Qwen3-1.7B_dynamic_wi4b32_afp32.litertlm`
- Quantization: dynamic INT4, block-32 weights / FP32 activations
- Context: 4096
- Size: roughly 932–977 MB depending on displayed artifact metadata

Registry ID: `qwen3-1.7b`.

## Runtime
Nano uses `litert-lm serve` because the official server exposes OpenAI-compatible `/v1/models` and `/v1/chat/completions`. LiteRT-LM also supports direct `litert-lm run`.

## Model management
```bash
litert-lm list
litert-lm import --from-huggingface-repo=litert-community/Qwen3-1.7B Qwen3-1.7B_dynamic_wi4b32_afp32.litertlm qwen3-1.7b
```
Nano's `download-model` / `import-model` commands call this CLI operation.

## Configuration
`NANO_LITERT_URL`, `NANO_LITERT_MODEL`, `NANO_LITERT_TIMEOUT`, `NANO_MAX_CONTEXT`, and `NANO_MODEL_NAME` control Nano's integration. LiteRT-LM's own `config.json` remains the source of truth for backend-specific runtime settings.
