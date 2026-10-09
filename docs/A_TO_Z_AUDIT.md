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
| Scheduler | Persistent interval jobs, enable/pause/delete, run history; assistant-prompt jobs only | `nano/scheduler.py`, `/api/scheduler/jobs`, `/api/scheduler/runs` |
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
10. **Production operations:** no multi-user tenancy, roles/permissions, secret vault, distributed scheduler, job retry policy, or audit-grade authorization.
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
