# Nano AI

Nano AI is a lightweight, privacy-first local talking assistant built around Qwen3 1.7B and the LiteRT-LM CLI.

## Runtime

Nano uses the official LiteRT-LM CLI as its inference runtime. LiteRT-LM provides an OpenAI-compatible local server on port 9379, so Nano sends chat requests to /v1/chat/completions.

Selected Qwen3 1.7B artifact: Qwen3-1.7B_dynamic_wi4b32_afp32.litertlm, about 932 MB, 4096-token context variant.

## Linux / macOS

    git clone https://github.com/abdulraheemnohri/Nano-AI.git
    cd Nano-AI
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -e .
    pip install -U litert-lm
    nano-ai init
    nano-ai download-model

Start LiteRT-LM:

    nano-ai litert-lm

Or directly:

    litert-lm serve --host 127.0.0.1 --port 9379

Start Nano Web UI in another terminal:

    nano-ai web

Open http://127.0.0.1:8000.

## Windows PowerShell

    git clone https://github.com/abdulraheemnohri/Nano-AI.git
    cd Nano-AI
    py -3 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -e .
    pip install -U litert-lm
    nano-ai init
    nano-ai download-model
    nano-ai litert-lm

Then open another PowerShell window, activate the environment and run nano-ai web.

## LiteRT-LM model

Nano's download-model command calls the LiteRT-LM CLI import operation:

    litert-lm import --from-huggingface-repo=litert-community/Qwen3-1.7B Qwen3-1.7B_dynamic_wi4b32_afp32.litertlm qwen3-1.7b

Then the CLI server loads the local registry:

    litert-lm serve --host 127.0.0.1 --port 9379

Default model ID: qwen3-1.7b.

## Voice

Install voice support with requirements-voice.txt. Voice flow is: Microphone -> local WAV -> Vosk STT -> Qwen3 1.7B through LiteRT-LM -> Piper TTS -> speaker.

No browser SpeechRecognition or cloud audio processing is required.

## UI

Talk supports conversations, microphone recording, WAV upload and TTS playback. Memory supports search and forgetting individual entries. Learning shows explicit learning events. Skills can be enabled or disabled. Knowledge imports local text. Model and System pages expose LiteRT-LM runtime state.

## CLI

    nano-ai --help
    nano-ai init
    nano-ai status
    nano-ai model
    nano-ai download-model
    nano-ai litert-lm
    nano-ai web

## Configuration

NANO_LITERT_URL defaults to http://127.0.0.1:9379. NANO_LITERT_MODEL defaults to qwen3-1.7b. Other settings include NANO_MODEL_NAME, NANO_MAX_CONTEXT, NANO_TEMPERATURE, NANO_LEARNING_ENABLED, NANO_STT_MODEL, NANO_PIPER_COMMAND and NANO_PIPER_VOICE.

## Security

Nano is local-first with no Firebase, mandatory cloud AI, terminal executor, browser automation, device-control agent or arbitrary plugin execution. Keep local HTTP services bound to localhost unless you add your own authentication and network controls.

## Tests

    python -m pytest