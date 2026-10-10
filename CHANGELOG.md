# Changelog

Notable changes to Nano AI are documented here. Releases follow the repository's audit-driven improvement phases.

## 0.5.x - 2026-10

### Added
- Memory search is paginated: `GET /api/memories` accepts a bounded `limit` (default 50, hard cap 500) and a non-negative `offset`; the Memory page loads 50 memories at a time with a "Load more memories" button.
- Opt-in automatic dependency install during updates: `POST /api/system/update/apply` accepts `install_dependencies`; when changed dependency files are detected and the flag is set, Nano runs pip against `requirements.txt` (or an editable install) and records the outcome in the recovery manifest. Restart remains manual by design.
- Learning events and Knowledge lists are now paginated (`limit`/`offset` query parameters; UI "Load more" buttons).
- Theme toggle button in the sidebar (light/dark, persisted through the theme setting).
- Disk-space guard: model imports (auto setup, custom import task, direct import) are refused with a clear message when under 3 GiB free space in the model directory.
- Conversation messages are paginated: `GET /api/conversations/{id}/messages` returns the newest window (default 200, max 500) in chronological order with `limit`/`offset`; the Talk UI shows a "Load earlier messages" button for long conversations.
- Bounded `GET /api/conversations` list (`limit` query parameter, default 200, capped at 500; `offset` for paging) so the sidebar no longer loads every conversation. The Talk sidebar loads conversations in pages of 200 with a "Load more conversations" button when more exist.
- Restore now prunes old `recovery/pre-restore-*.sqlite3` snapshots, keeping only the 10 newest, so repeated restores cannot fill the disk.
- Conversation management: `regenerate()` in core plus `POST /api/chat/regenerate`, `GET /api/conversations/search?q=` (LIKE search with escaped wildcards), and `GET /api/conversations/{cid}/export`. The Talk UI gained conversation search, Regenerate, Rename, Delete, and Export controls.
- Scheduler per-job hard timeout: new `timeout_seconds` column on `scheduled_jobs` (default 300, range 5-86400). Model requests run in a daemon worker thread; timeouts are recorded as `JobTimeoutError` attempts and follow the existing bounded retry policy. `POST /api/scheduler/jobs` accepts `timeout_seconds`, and the Automation UI exposes a run-timeout field.
- Model page now renders served models (from the running LiteRT-LM endpoint) separately from registry models (`litert-lm list`), highlighting the configured model.

### Fixed
- Web research text extraction emitted the literal two-character sequence `\n` instead of a newline at block-tag boundaries, polluting fetched page text and ingested knowledge with stray backslash-n characters. The extractor and the `research_and_learn` ingest header now use real newlines.
- Dashboard dead-script bug: a missing `cancelAutoModel` element crashed the whole UI script; the button and progress bar now exist.
- Honest `/api/ready` and `/api/health`: readiness now uses the tri-state `model_readiness()` classifier (endpoint unreachable / reachable but model not served / served). `/api/ready` returns 503 with actionable detail when the model is not served, and the UI header shows all three states.
- Model readiness diagnostics (`nano-ai doctor`, System health) now distinguish endpoint-unreachable from reachable-but-model-unserved instead of reporting a false "ready".

### Validation
- New automated coverage: `tests/test_web_ui.py` (every `$('id')` script reference must exist in the HTML), `tests/test_readiness_api.py`, `tests/test_conversations_api.py`, and scheduler timeout tests in `tests/test_scheduler_reliability.py`.
- Run `python -m pytest -q` locally and confirm GitHub Actions is green before tagging any release.