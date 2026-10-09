# Nano-AI A-to-Z Feature Audit

Audit scope: current `main` source tree. This document distinguishes shipped code from partial workflows and planned work; it is not a claim that every feature has passed runtime testing.

## Implemented in the repository

| Area | Current capability | Key files / API |
|---|---|---|
| Chat | Conversations, message history, local LiteRT-LM OpenAI-compatible endpoint | `nano/core.py`, `nano/model.py`, `/api/chat` |
| Local data | SQLite-backed conversations, memories, knowledge and learning events | `nano/db.py`, `nano/memory.py`, `nano/knowledge.py` |
| Skills | Seeded skills, enable/disable, proposal and approval flow | `nano/skills.py`, `/api/skills` |
| Local tools | Allowlisted calculator, datetime, unit conversion, text statistics, memory and knowledge search | `nano/tools.py`, `/api/tools` |
| Model management | Runtime status, registry listing, validated imports, user-triggered default setup, background custom import status | `nano/model_manager.py`, `/api/models` |
| Web research | HTTPS search, bounded readable-page extraction, local knowledge ingestion, private-host checks | `nano/research.py`, `/api/research` |
| Voice | Optional local Vosk transcription and Piper speech synthesis | `nano/voice.py`, `/api/voice` |
| Settings | Validated persisted settings and reset | `nano/settings.py`, `/api/settings` |
| Data portability | JSON export and consistent SQLite snapshot download | `/api/export`, `/api/backup` |
| Web UI | Talk, memory, learning, skills, knowledge, tools, model, settings, system and research pages | `nano/web.py` |
| Packaging | Python package/CLI, optional voice/test extras, GitHub Actions test workflow | `pyproject.toml`, `.github/workflows/` |

## Recent workflow completion

- The Model page submits custom model imports to `POST /api/models/import-task` instead of holding the browser request open while LiteRT-LM imports the model.
- The page polls `GET /api/models/auto-setup` for task state and refreshes model information on completion.
- Settings includes a direct SQLite backup download link.
- `tests/test_model_import_task.py` covers validation and the queued/running/completion lifecycle.
- `tests/test_backup.py` covers a valid snapshot and missing database behavior.

## Partial or missing; do not advertise as implemented

1. **Authentication and remote access:** API has no built-in user authentication. Keep both Nano and LiteRT-LM on loopback; do not expose the API to a LAN or public network without an authentication/TLS layer.
2. **Model import cancellation/progress percentage:** status is coarse-grained; there is no cancellation endpoint or percentage based on CLI progress.
3. **Web research network pinning:** DNS validation and redirect checks exist, but a hardened pinned-IP HTTP transport against DNS rebinding is not implemented.
4. **Restore workflow:** a consistent backup can be downloaded and checked, but in-app restore/rollback is not implemented. Restore manually while the service is stopped and retain the old database.
5. **Browser automation:** readable HTML extraction is implemented; JavaScript-capable browsing, login sessions, and computer control are not.
6. **Autonomous scheduling/agents:** no general background agent scheduler, multi-agent delegation, terminal executor, or device control is implemented.
7. **Cloud/channel integrations:** no mandatory cloud service; Telegram, WhatsApp, Discord, Slack, email, and MCP channel integrations are not implemented.
8. **Model compatibility:** LiteRT-LM is the supported inference path; arbitrary runtimes/providers are not interchangeable without adapters.
9. **Production operations:** no built-in multi-user tenancy, audit-grade access control, secret vault, or production deployment hardening.
10. **Verification:** source-level presence does not mean all tests passed. Run `python -m pip install -e ".[test]"` and `python -m pytest -q` in a clean environment; verify GitHub Actions before release.

## Security and recovery checklist

- Keep `NANO_HOST=127.0.0.1` and LiteRT-LM bound to `127.0.0.1`.
- Treat web research results and imported knowledge as untrusted reference text.
- Review skill proposals before enabling them.
- Download backups regularly and validate with `PRAGMA integrity_check`.
- Before manual restore, stop Nano, copy the current database, replace it with a verified snapshot, then restart and check `/api/health`.
- Do not run arbitrary commands or scripts suggested by model output.
