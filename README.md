# Nano AI

## Self-X: goals, planning, learning and research

Nano AI now includes a local-first, policy-bounded Self-X foundation. It tracks persistent goals, decomposes them into ordered plans and explicit task records, records lessons and reflections, stores research provenance, evaluates answer feedback, and generates reviewable improvement proposals.

- `GET /api/self/status`, `POST /api/self/check` — read-only diagnostics and runtime readiness.
- `GET /api/self/evaluation` — descriptive local feedback and quality metrics; no model-weight changes.
- `GET/POST /api/self/goals`, `PATCH /api/self/goals/{id}` — prioritized goals.
- `GET/POST /api/self/plans`, `GET /api/self/plans/{id}`, `PATCH /api/self/plans/{id}` — goal-linked plans and progress.
- `PATCH /api/self/tasks/{id}` — explicit task status/outcome recording. Completing every step completes its plan and goal.
- `GET/POST /api/self/lessons`, `POST /api/self/reflections` — persistent learning notes and reflection history.
- `GET/POST /api/self/research` — store source URLs, summaries, confidence, assessment and evidence.
- `POST /api/self/research/fetch` — fetch public HTTPS material through the existing SSRF-hardened client, index it locally, and record its provenance as unassessed.
- `GET/POST /api/self/improvements`, `PATCH /api/self/improvements/{id}` — review improvement proposals.
- `POST /api/self/review-cycle` — summarize local task and feedback signals, record a reflection, and propose an improvement when warranted.

These endpoints do not automatically execute plans, generated code, or proposals; change permissions; bypass approvals; or modify model weights. Web pages are untrusted evidence and should be independently cross-checked. Research fetch is an explicit user-initiated operation.

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

### Web UI files

The responsive single-page UI is implemented with plain HTML, CSS, and JavaScript (no frontend framework):

- `nano/static/index.html` — app shell and all 11 navigable pages.
- `nano/static/app.css` — dark-first theme, light-theme overrides, responsive layout, panels, forms, and chat styling.
- `nano/static/app.js` — page navigation, API calls, chat, pagination, model management, memory, learning, skills, tools, research, automation, settings, and system controls.
- `nano/web.py` — loads the packaged UI assets.
- `nano/app.py` — serves the page at `/`, stylesheet at `/assets/nano.css`, and JavaScript at `/assets/nano.js`.

UI sections: Talk, Memory, Learning, Skills, Tools, Knowledge, Web Research, Automation & Agents, Model, Settings, and System. The existing backend APIs remain the source of truth; UI controls use the corresponding API routes rather than mock data.

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

List tools with `GET /api/tools`. Execute a tool with `POST /api/tools/run`, using JSON such as `{"name":"calculator","arguments":{"expression":"(2+3)*4"}}`. Enable or disable one with `POST /api/tools/{name}/enabled?enabled=false`. Tool calls are logged to the local learning-event history. The API is protected by an optional bearer token for local use and requires a configured token for remote access. Set `NANO_API_TOKEN` before exposing Nano; also use TLS and firewall controls.

Built-in tools remain local and allowlisted. Optional restricted terminal and Playwright browser controls are available through the Automation & Agents page; they require explicit approvals and never provide arbitrary shell execution.

## Automatic model setup

Open the Model page and choose **Auto setup / download default model**. Nano checks whether the LiteRT-LM CLI is installed and whether the configured Qwen3 1.7B model is listed in the registry. If it is missing, Nano runs the project's configured LiteRT-LM import operation in a background task and exposes status at `GET /api/models/auto-setup`. Starting setup is an explicit user action because the model may require about 1 GB of storage and bandwidth. The setup process does not silently download models on application startup. The Model page also provides a custom import form for a user-supplied Hugging Face repository, exact artifact filename, and local model ID; use artifact names supported by your installed LiteRT-LM release. For API clients, `POST /api/models/import-task` queues a validated custom import without holding the request open; poll `GET /api/models/auto-setup` for `queued`, `running`, `complete`, or `error` state. Only one model setup/import task can run at a time.

The Model page also renders two separate model lists: **served models** reported by the running LiteRT-LM endpoint (`/v1/models`) and **registry models** reported by the local `litert-lm list` command, with the configured model highlighted. Readiness is tri-state: the endpoint can be unreachable, reachable but not serving the configured model, or serving it. `GET /api/health` and `GET /api/ready` use the same classifier, and `/api/ready` returns 503 with an actionable detail message when the configured model is not served.

## Live system health dashboard

Open **System** in the Nano AI web UI and use **Refresh health** to inspect live, read-only status from the running process. The dashboard shows SQLite integrity and conversation/message/memory counts, LiteRT-LM endpoint connectivity, scheduler worker status, recent failed/interrupted scheduled runs, and optional Vosk/Piper readiness. Raw JSON is available for troubleshooting.

The same snapshot is available from `GET /api/system/health`. Health inspection does not restart workers, repair the database, or change configuration. A warning indicates an unavailable optional service or a condition that needs review; use the detailed check message before taking action.

## Installation diagnostics

Run the read-only diagnostic command after installation:

    nano-ai doctor

It checks the Python version, directory writability, SQLite integrity and required tables, API binding/authentication posture, LiteRT-LM CLI/endpoint reachability, and optional browser/voice availability. It prints JSON and exits non-zero for critical failures. Warnings such as a stopped model server are actionable but do not block launching the UI. The command does not install dependencies, download a model, change settings, or start services.

## Project audit

See [docs/A_TO_Z_AUDIT.md](docs/A_TO_Z_AUDIT.md) for an implementation inventory, known gaps, security constraints, and verification checklist. It explicitly separates shipped features from planned or partial capabilities. See [docs/FINAL_RELEASE_REVIEW.md](docs/FINAL_RELEASE_REVIEW.md) for the final A-to-Z release decision, automated-test evidence, target-machine release gate, and explicit non-goals. Notable user-facing changes are tracked in [CHANGELOG.md](CHANGELOG.md).

## Automation, agents, authentication, channels and MCP

The **Automation & Agents** page provides persistent recurring assistant-prompt jobs, run history, specialist delegation, a fixed allowlisted terminal runner, optional Playwright browser actions, Telegram/webhook send controls, and an MCP tools-list tester. Scheduler jobs are stored in SQLite and require at least a 60-second interval. Specialist roles use the configured local model with different instructions; they are not separate distributed model instances.

Model imports expose a progress percentage, current phase, and cancellation endpoint. Some LiteRT-LM CLI versions do not report true percentage progress; in that case Nano clearly marks its displayed percentage as an estimate. Cancel with `POST /api/models/auto-setup/cancel`.

### Authentication and remote access

Set a strong random token in `NANO_API_TOKEN`. The UI prompts for it when the API returns 401 and keeps it in the current browser tab's session storage. Use `Authorization: Bearer YOUR_TOKEN` or `X-Nano-Token: YOUR_TOKEN` for API clients. The CLI refuses non-loopback binding without this token; also configure TLS, firewall rules, and a reverse proxy appropriately.

### Request limits, settings, and recovery

- `NANO_MAX_REQUEST_BYTES=1048576` limits JSON/API request bodies (default 1 MiB; maximum configurable value 10 MB), including chunked requests without `Content-Length`. Restore and voice uploads use separate streaming limits.
- `NANO_RATE_LIMIT_PER_MINUTE=120` limits API calls per client IP per process. Multi-worker deployments should also configure reverse-proxy rate/body limits.
- Settings have a schema endpoint at `GET /api/settings/schema`, including descriptions, defaults, choices and numeric bounds. Theme, language, model parameters, memory limits, knowledge list size, learning, and voice toggles are wired to runtime/UI behavior.
- Settings offers a SQLite backup restore upload at `POST /api/restore`. Restore checks database integrity and required tables, creates a pre-restore snapshot in `data/recovery/`, and reports its filename. Keep this directory private.

### Optional integrations

- `NANO_TELEGRAM_BOT_TOKEN`: Telegram outbound messages.
- `NANO_TELEGRAM_WEBHOOK_SECRET`: validate inbound Telegram webhook updates at `POST /api/channels/telegram/webhook`.
- `NANO_WEBHOOK_ALLOWED_HOSTS`: comma-separated allowlist for additional HTTPS webhook hosts. Slack and Discord webhook hosts are pre-allowed.
- `pip install -e ".[browser]"` plus the matching Playwright browser installation enables guarded browser control. Set `NANO_BROWSER_ALLOWED_HOSTS` for additional sites.
- `pip install -e ".[desktop]"` enables optional desktop control dependencies. Set `NANO_ENABLE_DESKTOP_CONTROL=true` to opt in on that machine; screenshot is read-only and input actions require approval.
- `POST /mcp` exposes a minimal JSON-RPC MCP-style `tools/list` and `tools/call` interface over the enabled built-in tools.

WhatsApp, email, full MCP transport variants, unrestricted terminal access, persistent browser sessions, and distributed multi-model agent swarms are not implemented in this version.

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

## Conversation management

Talk supports searching conversations by message text (`GET /api/conversations/search?q=`), renaming and deleting conversations, exporting a single conversation as JSON (`GET /api/conversations/{id}/export`), and regenerating the latest answer (`POST /api/chat/regenerate` removes the newest assistant reply and re-runs the model on the last user message without duplicating it). Search escapes SQL wildcard characters and returns a bounded number of results.

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


## Conversation improvement and autonomous talk

Nano supports explicit per-answer feedback (helpful/not helpful plus an optional correction). Recent corrections are added to future model context as guidance, and the Learning page displays feedback totals. This is auditable local context adaptation, not silent model-weight training. The Learning page also reports explicit-feedback rates and a 7-day comparison; these are descriptive user ratings, not proof that model quality objectively improved. The report is available at GET /api/learning/quality.

Autonomous voice check-ins are disabled by default. In Settings, enable `autonomous_talk_enabled`, keep `voice_enabled` and `auto_tts` enabled, choose a 10-minute to 24-hour interval, and customize the prompt. Check-ins run only while the web UI is open, visible, and idle; they are logged in the local learning-event history.

## GitHub update lifecycle

The System page can check the official `abdulraheemnohri/Nano-AI` main branch. Applying an update requires explicit confirmation, a clean working tree, the main branch, and the expected official GitHub origin; updates are fast-forward-only. The updater does not install packages or restart the app. Review dependency changes, install them manually if required, and restart Nano AI after an update. Back up the database before updating.


### Update recovery and rollback

The System page's GitHub updater now creates an integrity-checked SQLite snapshot before applying a fast-forward update and records a recovery manifest with the previous/current commit and dependency manifest changes. The UI can roll code back to the recorded previous commit after explicit confirmation. Restoring the pre-update database is a separate, additional confirmation because it overwrites current data. Rollback requires the clean `main` branch and the exact recorded updated HEAD; it refuses to reset if the checkout has moved. Review and back up current data before recovery. Package installation and restart remain manual.


### Memory consolidation review

The Memory page can scan for exact duplicates and highly similar active memories, then queue suggestions for manual review. Nano never merges memories during scanning. Approving a proposal creates a new active memory and marks its source records as `merged` in one SQLite transaction; rejecting leaves the originals untouched. The proposal text is editable before approval. API routes are `GET /api/memories/duplicates`, `GET /api/memories/consolidation`, `POST /api/memories/consolidation/scan`, and the proposal-specific `approve` / `reject` endpoints.


## Scheduler retries and recovery

Recurring assistant-prompt jobs support a bounded retry policy with exponential backoff. Configure the maximum attempts and base retry delay when creating a job. The Automation & Agents page shows the last error and provides a manual Retry now action. Startup marks unfinished runs as interrupted and schedules a retry when attempts remain. Each job also has a hard per-job run timeout (`timeout_seconds`, default 300 seconds, range 5-86400). The model request runs in a worker thread; if it exceeds the timeout, the attempt is recorded as a `JobTimeoutError` and the bounded retry policy applies. Configure it when creating a job or through `POST /api/scheduler/jobs`. This scheduler is an in-process, single-worker feature, not a distributed task queue. See docs/A_TO_Z_AUDIT.md for the complete feature inventory and limitations.
