# Nano AI

Nano AI is a lightweight, privacy-first local talking assistant built around Qwen3 1.7B and the LiteRT-LM CLI. It includes persistent learning, reusable prompt skills, optional offline voice, and a bounded local tool registry.

## Runtime

Nano uses the official LiteRT-LM CLI as its inference runtime. LiteRT-LM provides an OpenAI-compatible local server on port 9379, so Nano sends chat requests to `/v1/chat/completions`.

Selected Qwen3 1.7B artifact: `Qwen3-1.7B_dynamic_wi4b32_afp32.litertlm`, about 932 MB, 4096-token context variant.

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

Then open another PowerShell window, activate the environment and run `nano-ai web`.

## LiteRT-LM model

Nano's `download-model` command calls the LiteRT-LM CLI import operation:

    litert-lm import --from-huggingface-repo=litert-community/Qwen3-1.7B Qwen3-1.7B_dynamic_wi4b32_afp32.litertlm qwen3-1.7b

Then the CLI server loads the local registry:

    litert-lm serve --host 127.0.0.1 --port 9379

Default model ID: `qwen3-1.7b`.

## Built-in tools

Nano exposes a small, allowlisted tool registry through its local API:

- `calculator`: bounded arithmetic expression evaluation; no Python eval or code execution.
- `datetime_now`: system-local and UTC timestamps.
- `unit_convert`: common length, mass, temperature, and digital-storage conversions.
- `text_stats`: character, word, line, and sentence counts.
- `memory_search`: search saved memories.
- `knowledge_search`: search locally imported knowledge.

List tools with `GET /api/tools`. Execute a tool with `POST /api/tools/run`, using JSON such as `{"name":"calculator","arguments":{"expression":"(2+3)*4"}}`. Enable or disable one with `POST /api/tools/{name}/enabled?enabled=false`. Tool calls are logged to the local learning-event history. These endpoints are intended for the localhost-only UI/API; add authentication before exposing Nano to a network.

Tools do not run shell commands, arbitrary Python, browser automation, or external network requests.

## Automatic model setup

Open the Model page and choose **Auto setup / download default model**. Nano checks whether the LiteRT-LM CLI is installed and whether the configured Qwen3 1.7B model is listed in the registry. If it is missing, Nano runs the project's configured LiteRT-LM import operation in a background task and exposes status at `GET /api/models/auto-setup`. Starting setup is an explicit user action because the model may require about 1 GB of storage and bandwidth. The setup process does not silently download models on application startup. The Model page also provides a custom import form for a user-supplied Hugging Face repository, exact artifact filename, and local model ID; use artifact names supported by your installed LiteRT-LM release. For API clients, `POST /api/models/import-task` queues a validated custom import without holding the request open; poll `GET /api/models/auto-setup` for `queued`, `running`, `complete`, or `error` state. Only one model setup/import task can run at a time.

## Project audit

See [docs/A_TO_Z_AUDIT.md](docs/A_TO_Z_AUDIT.md) for an implementation inventory, known gaps, security constraints, and verification checklist. It explicitly separates shipped features from planned or partial capabilities.

## Development and tests

Install the test extra and run the suite:

    python -m pip install -e ".[test]"
    python -m pytest -q

GitHub Actions runs the test suite on pushes to `main`, pull requests targeting `main`, and manual workflow dispatch. Model import requests validate the Hugging Face repository, `.litertlm` artifact filename, and model ID before invoking LiteRT-LM; the CLI import is bounded by a two-hour timeout. Invalid input returns HTTP 400, while runtime/import failures return HTTP 503.

## Web research and local learning

Open **Web Research**, search the web, then choose a result to read and save to Nano's local knowledge database. You can also paste a public HTTPS page URL. Nano limits page size and supported content types, blocks local/private network targets, and extracts readable text without executing page JavaScript. Research endpoints are `POST /api/research/search` and `POST /api/research/learn`. Web content is untrusted reference material; it is not run as code or treated as system instructions. Searching and fetching pages require an internet connection; saved knowledge remains in Nano's local database.

## Voice

Install voice support with `pip install -r requirements-voice.txt`. Voice flow is: Microphone -> local WAV -> Vosk STT -> Qwen3 1.7B through LiteRT-LM -> Piper TTS -> speaker.

No browser SpeechRecognition or cloud audio processing is required.

## UI

Talk supports conversations, microphone recording, WAV upload and TTS playback. Memory supports search and forgetting individual entries. Learning shows learning events. Skills can be enabled or disabled and proposed skills require approval. Knowledge imports local text. Model and System pages expose LiteRT-LM runtime state. The Tools page lists built-in tools, provides enable/disable switches, and includes a manual JSON runner. The Model page offers user-triggered automatic model setup, and Web Research lets users search, fetch, and save selected public pages to local knowledge. Talk recognizes supported explicit commands such as `calculate 2 + 2`, `convert 1 km to m`, `search my memory for solar`, `search local knowledge for inverter`, and `count words in: hello world`.

## CLI

    nano-ai --help
    nano-ai init
    nano-ai status
    nano-ai model
    nano-ai download-model
    nano-ai litert-lm
    nano-ai web

## Configuration

`NANO_LITERT_URL` defaults to `http://127.0.0.1:9379`. `NANO_LITERT_MODEL` defaults to `qwen3-1.7b`. Other settings include `NANO_MODEL_NAME`, `NANO_MAX_CONTEXT`, `NANO_TEMPERATURE`, `NANO_LEARNING_ENABLED`, `NANO_STT_MODEL`, `NANO_PIPER_COMMAND` and `NANO_PIPER_VOICE`. Tool enablement is persisted in the local settings database.

## Database backup

Download a consistent SQLite snapshot from `GET /api/backup` while Nano is running. The endpoint uses SQLite's online backup API so the snapshot includes committed data even when WAL mode is in use. Verify a downloaded backup before relying on it:

    python -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); print(c.execute('PRAGMA integrity_check').fetchone()[0]); c.close()" nano-ai-backup.sqlite3

The expected output is `ok`. Keep backups private because they can contain conversation history, memories, and imported knowledge. Restoring is intentionally a manual operation: stop Nano, preserve a copy of the current database, then replace the configured database file with a verified backup.

## Security

Nano is local-first and does not require Firebase or cloud AI. Built-in tools are allowlisted and validated. Keep local HTTP services bound to localhost unless you add authentication and network controls.

## Tests

    python -m pytest
