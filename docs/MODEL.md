# Model and LiteRT-LM Runtime

Nano AI defaults to the official LiteRT-LM Qwen3-4B-Thinking-2507 block-32 artifact requested for this project. It does not use GGUF or llama.cpp.

## Default artifact

- Repository: `litert-community/Qwen3-4B-Thinking-2507`
- Artifact: `Qwen3_4b_thinking_dynamic_wi4b32_afp32.litertlm`
- Registry ID: `qwen3-4b-thinking-2507`
- Format: LiteRT-LM `.litertlm`, dynamic INT4 block-32 weights with FP32 activations
- Context: 4096 tokens
- Download size: approximately 2.1 GB; reserve at least 3 GB free disk space for import/cache.
- Memory: this 4B reasoning model can need several GB of RAM; 8 GB or more is recommended. 6 GB machines may be memory-constrained, depending on OS, backend, and other applications.
- Reasoning: allow enough generation tokens (typically at least 2048) or the response may stop before its final answer.

Model card and artifact: https://huggingface.co/litert-community/Qwen3-4B-Thinking-2507/blob/main/Qwen3_4b_thinking_dynamic_wi4b32_afp32.litertlm

## Import and run

```bash
python -m pip install -U litert-lm
nano-ai download-model
litert-lm list
nano-ai litert-lm
```

Equivalent explicit import command:

```bash
litert-lm import --from-huggingface-repo=litert-community/Qwen3-4B-Thinking-2507 Qwen3_4b_thinking_dynamic_wi4b32_afp32.litertlm qwen3-4b-thinking-2507
```

Nano uses `litert-lm serve` because the CLI exposes the local OpenAI-compatible `/v1/models` and `/v1/chat/completions` endpoints. Keep the service on loopback. In a second terminal run `nano-ai web`, then open http://127.0.0.1:8000.

## Model management and configuration

`nano-ai download-model` imports the default artifact. For an alternate model, pass `--repo OWNER/REPO --file artifact.litertlm --id registry-id`. Use only repository and artifact names verified on Hugging Face and supported by your installed LiteRT-LM version.

`NANO_LITERT_URL`, `NANO_LITERT_MODEL`, `NANO_LITERT_TIMEOUT`, `NANO_MAX_CONTEXT`, and `NANO_MODEL_NAME` control Nano's integration. LiteRT-LM's own model metadata remains the source of truth for backend-specific runtime settings.

## Troubleshooting

- Endpoint unreachable: start `nano-ai litert-lm` and check `nano-ai status`.
- Model ID not served: run `litert-lm list`; set `NANO_LITERT_MODEL` to the exact ID shown by `/v1/models`.
- Out of memory: close other applications, use a machine with more RAM, or explicitly import a smaller supported LiteRT-LM model.
- Slow first response: the model is a reasoning model and may spend tokens thinking before answering.
