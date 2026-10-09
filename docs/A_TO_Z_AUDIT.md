# Nano AI A-to-Z Feature Audit

Audit scope: current `main` source tree. This inventory distinguishes implemented code from constrained integrations and remaining production gaps. Source presence is not proof of a passing runtime test suite.

## Implemented capabilities

| Area | Capability | Key files / endpoints |
|---|---|---|
| Chat and history | SQLite conversations, messages, model-backed responses | `nano/core.py`, `nano/db.py`, `/api/chat` |
| Local data | Memories, knowledge ingestion/search, learning event history | `nano/memory.py`, `nano/knowledge.py`, `nano/learning.py` |
| Skills | Enabled skills and proposal approval/rejection | `nano/skills.py`, `/api/skills` |
| Built-in tools | Bounded calculator, time, unit conversion, text stats, memory/knowledge search | `nano/tools.py`, `/api/tools` |
| Model management | Validated background import, cancellation, best-effort percentage/estimate, persistent task status and interrupted-task recovery | `nano/model_manager.py`, `/api/models/auto-setup`, `/api/models/import-task/cancel` |
| Scheduler | Persistent interval jobs, enable/pause/delete, bounded exponential retries, manual retry, interrupted-run recovery, run history; assistant-prompt jobs only | `nano/scheduler.py`, `/api/scheduler/jobs`, `/api/scheduler/runs` |
| Delegation | Researcher/coder/planner/reviewer/writer specialist prompts, bounded task size and timeout | `nano/agents.py`, `/api/agents/delegate` |
| Authentication | Bearer token / X-Nano-Token, remote peer guard, CLI remote-bind guard | `nano/security.py`, `nano/app.py`, `nano/cli.py` |
| Terminal | Fixed command allowlist, no shell, workspace path guard, per-action approval | `nano/terminal.py`, `/api/terminal/run` |
| Browser | Optional Playwright inspect/click/fill, host allowlist, approval for click/fill | `nano/browser.py`, `/api/browser/action` |
| Desktop | Optional PyAutoGUI screenshot and bounded click/type/key actions; disabled by default | `nano/desktop.py`, `/api/computer/action` |
| Messaging | Telegram send + secret-validated inbound webhook, HTTPS Slack/Discord/custom webhook delivery | `nano/messaging.py`, `/api/channels/*` |
| MCP | Minimal JSON-RPC `initialize`, `ping`, `tools/list`, and `tools/call` over HTTP | `nano/mcp.py`, `POST /mcp` |
| Research | HTTPS search, bounded readable-page extraction and local ingestion | `nano/research.py`, `/api/research` |
| Voice | Optional local Vosk transcription and Piper speech synthesis | `nano/voice.py`, `/api/voice` |
| Data recovery | JSON export, consistent SQLite snapshot, validated restore, integrity checks and pre-restore recovery snapshot | `/api/export`, `/api/backup`, `/api/restore` |
| Settings | Typed schema with defaults/descriptions, validated ranges and active theme/voice/learning/model parameters | `nano/settings.py`, `/api/settings/schema` |
| UI | Talk, memory, learning, skills, tools, knowledge, research, model, automation/agents, settings and system | `nano/web.py` |

## Important limitations

1. **Progress fidelity:** LiteRT-LM releases do not expose a consistent progress protocol. Nano parses percentages when present; otherwise it shows a clearly labelled estimate, not verified download bytes.
2. **Delegation semantics:** specialist agents currently use the same configured model with different role prompts. Batch delegation is bounded and sequential; this is not a distributed multi-model swarm.
3. **Terminal scope:** the terminal runner is intentionally read-oriented and allowlisted. It does not provide unrestricted shell access, arbitrary scripts, sudo, or destructive commands.
4. **Computer control:** Playwright browser control is optional and host-allowlisted. Desktop control is separately opt-in and approval-gated; it is not a full autonomous desktop agent, and sessions are not persistent.
5. **Messaging scope:** Telegram requires a bot token and webhook secret. Generic outgoing webhook delivery is supported for Slack/Discord or explicitly allowlisted HTTPS hosts. WhatsApp, email, Discord bot events, Slack event ingestion, and persistent channel polling are not implemented.
6. **MCP compatibility:** this is a minimal JSON-RPC HTTP endpoint, not a complete implementation of every MCP transport/version or OAuth flow.
7. **Research network pinning:** HTTPS sockets connect to a validated, pinned public IP with hostname TLS verification; redirects are revalidated and repinned. DNS rebinding tests cover mixed public/private DNS answers. Network-layer egress controls remain recommended.
8. **Restore workflow:** in-app restore checks integrity and schema, saves a recovery snapshot, and attempts rollback if applying the restore fails. Test restore behavior with representative real backups before production use.
9. **Request protections:** body-size limits use Content-Length and rate limits are per process; proxies should enforce limits for chunked requests and multi-worker deployments.
10. **Production operations:** no multi-user tenancy, roles/permissions, secret vault, distributed scheduler, forcibly cancellable per-job timeout, or audit-grade authorization. Retry policy is bounded and in-process only.
11. **Verification:** run `python -m pip install -e ".[test]"` and `python -m pytest -q`; confirm GitHub Actions before release.

## Security and recovery checklist

- Keep `NANO_HOST=127.0.0.1` unless remote access is intentional.
- Set a strong `NANO_API_TOKEN` before remote binding; configure TLS and firewall rules too.
- Keep `NANO_LITERT_URL` on loopback.
- Review scheduled prompts and skill proposals before enabling them.
- Require explicit approval for terminal/browser actions.
- Treat imported web pages and model output as untrusted.
- Download backups regularly and verify them with `PRAGMA integrity_check`.


## New conversational and update lifecycle additions

- **Explicit feedback loop:** per-answer helpful/unhelpful rating and optional correction stored in SQLite; recent corrections are injected into future model context. This changes response guidance, not model weights.
- **Autonomous talking:** opt-in local-model check-ins, configurable prompt and 10-1440 minute interval, only while the browser tab is visible and idle; local Piper TTS is required.
- **GitHub update lifecycle:** read-only update check plus explicit approved fast-forward update, blocked on dirty worktrees or non-main branches and restricted to the expected official origin. Dependency installation and process restart remain manual.
- **Validation:** tests cover feedback storage, correction retrieval, proactive-talk event logging, update checking, and the explicit-approval gate. Check the GitHub Actions result for the latest commit before release.


## Update recovery lifecycle

- The updater snapshots the current SQLite database using SQLite's online backup API and verifies the snapshot with `PRAGMA integrity_check` before changing code.
- An atomic recovery manifest records the previous and new commit IDs, database snapshot path, and dependency files changed.
- The System page offers a separately approved code rollback. Database restoration is a distinct opt-in checkbox with an additional destructive-action confirmation.
- Rollback refuses dirty worktrees, non-main branches, missing/unreadable manifests, or a HEAD that no longer matches the recorded update.
- Dependencies and service restart remain manual. These safeguards reduce risk but do not replace a separate verified backup and maintenance window.


## Feedback quality analytics

- Learning reports count helpful/unhelpful ratings and explicit corrections, overall helpful/correction rates, daily totals for the last 14 days, and a descriptive comparison of the last 7 days with the prior 7 days.
- Rates are omitted when there is insufficient feedback; the UI explicitly states these metrics do not prove causal model improvement.
- API: GET /api/learning/quality. Metrics use only locally stored explicit user feedback.


## Memory consolidation and duplicate review

- Duplicate detection suggests exact text matches and high token-overlap candidates; it is heuristic and requires human review.
- Scanning only creates review proposals. It never merges or deletes memories.
- The Memory UI shows source records and an editable consolidated text before approval.
- Approval validates that every source remains active, then atomically inserts the replacement and marks source records `merged`; rejecting preserves source records unchanged.
- API: `GET /api/memories/duplicates`, `GET /api/memories/consolidation`, `POST /api/memories/consolidation/scan`, `POST /api/memories/consolidation/{id}/approve`, and `POST /api/memories/consolidation/{id}/reject`.


## Scheduler reliability hardening (current implementation)

- Scheduled assistant-prompt jobs support bounded retry attempts (1-10) and exponential backoff from a configurable 5-3600 second base, capped at one hour.
- Each run records its attempt number and outcome. Failed attempts retain a bounded error message; a successful run clears retry state.
- Startup recovery marks stale running records as interrupted, clears orphaned claims, and schedules a bounded retry when attempts remain.
- The Automation & Agents UI shows retry settings and last errors, and offers an explicit manual retry action.
- API creation fields: max_attempts, retry_delay_seconds. Manual retry: POST /api/scheduler/jobs/{id}/retry.
- Scheduler remains a single-process in-app worker; it is not a distributed queue. A running model request is bounded by the LiteRT-LM request timeout, not a separate forcibly cancellable per-job timeout.

## Final A-to-Z review notes

- Repository inventory and docs are reviewed against the checked-in source tree. Implemented means code exists; the test suite and CI provide separate evidence, and external model/voice/browser integrations still require environment-specific validation.
- The two GitHub Actions workflows previously ran the same test command. Keep one canonical workflow to avoid duplicate CI executions.
- Release verification should include python -m pip install -e ".[test]", python -m pytest -q, a local LiteRT-LM smoke test, backup/restore rehearsal, and remote-access security checks if remote binding is enabled.
- Known non-goals/gaps remain: no multi-user tenancy/RBAC, no distributed scheduler, no unrestricted shell, no complete MCP transport/OAuth implementation, no native WhatsApp/email/Slack/Discord event adapters, no silent model-weight training, and no automatic dependency installation/restart during updates.


## Final-review release blocker — resolved

- Fixed `_write_recovery_manifest` in `nano/updates.py` to append an actual newline after the JSON document instead of the literal two-character sequence `\\n`.
- Added a regression test in `tests/test_final_review.py` that writes the recovery manifest, verifies the real trailing newline, rejects a literal backslash-n suffix, and parses the file with `json.loads`.
- The updater rollback path is now covered for this serialization defect. This does not replace the documented recommendation to rehearse a full update/rollback cycle against a disposable Git checkout and representative database before production use.

## Final release status

- Current release posture: **feature-complete for the documented local-first scope, but not a claim of production certification**.
- Run `python -m pip install -e ".[test]"` and `python -m pytest -q`; verify the latest GitHub Actions run before tagging a release.
- Also complete environment-specific LiteRT-LM inference, optional voice/browser/desktop, backup/restore, Windows PowerShell, and remote-access security smoke tests on the actual target machine.


## Installation diagnostics

- `nano-ai doctor` provides read-only installation checks for Python compatibility, configured directory writability, SQLite integrity/schema presence, API bind/auth policy, LiteRT-LM CLI and endpoint reachability, and optional browser/voice dependencies.
- It reports JSON, warns when the model endpoint is unavailable, and exits non-zero for critical failures such as remote binding without an API token or an invalid database.
- It does not initialize the database, install dependencies, fetch models, alter settings, or start services.
- Automated coverage: `tests/test_doctor.py` checks the healthy local setup and the remote-binding authentication guard.

## Model readiness diagnostics (Phase 2 improvement)

- `nano/runtime.py` now records an `endpoint_error` reason (connection refusal, HTTP status, or a parse failure) and exposes `model_readiness(runtime)`, a shared classifier for model readiness.
- `nano-ai doctor` and the live System health page now distinguish three states: endpoint unreachable (start hint: `nano-ai litert-lm`), endpoint reachable but the configured model is not served or the registry is empty (import hint: `nano-ai download-model`), and endpoint reachable with the configured model served (ok).
- Regression coverage lives in `tests/test_doctor.py` and `tests/test_system_health.py`. These are mocked endpoint tests; they are not evidence of real LiteRT-LM inference on a target machine.
