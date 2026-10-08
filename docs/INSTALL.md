# Nano AI — LiteRT-LM Installation Guide

## 1. Prerequisites
Linux, macOS and Windows are supported by LiteRT-LM. Install Python 3.10+ and Git.

    python3 --version
    git --version

Windows PowerShell:
    py --version
    git --version

## 2. Clone
    git clone https://github.com/abdulraheemnohri/Nano-AI.git
    cd Nano-AI

## 3. Python environment
Linux/macOS:
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -e .
    pip install -U litert-lm

Windows PowerShell:
    py -3 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -e .
    pip install -U litert-lm

## 4. Initialize
    nano-ai init
    nano-ai status

## 5. Import Qwen3 1.7B
Nano uses the LiteRT-LM Qwen3 1.7B dynamic INT4 artifact:
    litert-lm import --from-huggingface-repo=litert-community/Qwen3-1.7B Qwen3-1.7B_dynamic_wi4b32_afp32.litertlm qwen3-1.7b

Or use:
    nano-ai download-model

The model is imported into the LiteRT-LM local registry. Nano does not use GGUF or llama.cpp.

## 6. Start LiteRT-LM
Terminal 1:
    nano-ai litert-lm

Equivalent direct command:
    litert-lm serve --host 127.0.0.1 --port 9379

LiteRT-LM exposes an OpenAI-compatible local API at:
    http://127.0.0.1:9379/v1/models
    http://127.0.0.1:9379/v1/chat/completions

## 7. Start Nano
Terminal 2:
    nano-ai web
Open http://127.0.0.1:8000

## 8. Voice
Voice is optional:
    pip install -r requirements-voice.txt
Configure Vosk:
    NANO_STT_MODEL=models/vosk
Configure Piper:
    NANO_PIPER_COMMAND=piper
    NANO_PIPER_VOICE=models/piper/<voice>.onnx
Voice flow:
Microphone -> local WAV -> Vosk -> Qwen3 1.7B through LiteRT-LM -> Piper -> speaker.

## 9. Verify
    nano-ai status
    nano-ai model
    python -m pytest
Use System in the UI to inspect LiteRT-LM and voice status.

## 10. Offline operation
After LiteRT-LM, the model registry artifact, Vosk model and Piper voice are installed, Nano can operate without a cloud AI provider. Initial package/model downloads require internet unless transferred manually.

## 11. Troubleshooting
litert-lm not found: install with python -m pip install -U litert-lm.
LiteRT-LM server unreachable: run nano-ai litert-lm.
Model unavailable: run nano-ai download-model and check nano-ai status.
Wrong model ID: set NANO_LITERT_MODEL to the model ID shown by /v1/models.
Vosk model not found: verify NANO_STT_MODEL.
Piper executable not found: verify NANO_PIPER_COMMAND.
Microphone unavailable: grant browser permission or upload mono 16-bit PCM WAV.
Port conflict: use nano-ai litert-lm --port 9380 and set NANO_LITERT_URL=http://127.0.0.1:9380.

## 12. Data
Default database: data/nano.sqlite3. Local model files are under models/.