# Nano AI A-to-Z Feature Audit

Audit scope: current `main` source tree. This inventory distinguishes implemented code from constrained integrations and remaining production gaps. Source presence is not proof of a passing runtime test suite.

## Implemented capabilities

| Area | Capability | Key files / endpoints |
|---|---|---|
| Chat and history | SQLite conversations, messages, model-backed responses | `nano/core.py`, `nano/db.py`, `/api/chat` |
| Local data | Memories, knowledge ingestion/search, learning event history | `nano/memory.py`, `nano/knowledge.py`, `nano/learning.py` |
| Skills | Enabled skills and proposal approval/rejection | `nano/skills.py`, `/api/skills` |
| Built-in tools | Bounded calculator, time, unit conversion, text stats, memory/knowledge search | `nano/tools.py`, `/api/tools` |
| Model management | Validated background import, cancellation endpoint, phase/progress status | `nano/model_manager.py`, `/api/models/auto-setup`, `/api/models/import-task/cancel` |
| Scheduler | Persistent interval jobs, enable/pause/delete, run history; assistant-prompt jobs only | `nano/scheduler.py`, `/api/scheduler/jobs`, `/api/scheduler/runs` |
| Delegation | Researcher/coder/planner/reviewer/writer specialist prompts, bounded task size and timeout | `nano/agents.py`, `/api/agents/delegate` |
| Authentication | Bearer token / X-Nano-Token, remote peer guard, CLI remote-bind guard | `nano/security.py`, `nano/app.py`, `nano/cli.py` |
| Terminal | Fixed command allowlist, no shell, workspace path guard, per-action approval | `nano/terminal.py`, `/api/terminal/run` |
| Browser | Optional Playwright inspect/click/fill, host allowlist, approval for click/fill | `nano/browser.py`, `/api/browser/action` |
| Messaging | Telegram send + secret-validated inbound webhook, HTTPS Slack/Discord/custom webhook delivery | `nano/messaging.py`, `/api/channels/*` |
| MCP | Minimal JSON-RPC `initialize`, `ping`, `tools/list`, and `tools/call` over HTTP | `nano/mcp.py`, `POST /mcp` |
| Research | HTTPS search, bounded readable-page extraction and local ingestion | `nano/research.py`, `/api/research` |
| Voice | Optional local Vosk transcription and Piper speech synthesis | `nano/voice.py`, `/api/voice` |
| Portability | JSON export and consistent SQLite backup snapshot | `/api/export`, `/api/backup` |
| UI | Talk, memory, learning, skills, tools, knowledge, research, model, automation/agents, settings and system | `nano/web.py` |

## Important limitations

1. **Progress fidelity:** LiteRT-LM releases do not expose a consistent progress protocol. Nano parses percentages when present; otherwise it shows a clearly labelled estimate, not verified download bytes.
2. **Delegation semantics:** specialist agents currently use the same configured model with different role prompts. Batch delegation is bounded and sequential; this is not a distributed multi-model swarm.
3. **Terminal scope:** the terminal runner is intentionally read-oriented and allowlisted. It does not provide unrestricted shell access, arbitrary scripts, sudo, or destructive commands.
4. **Computer control:** Playwright is optional; host allowlisting is required for non-local websites. Browser sessions are short-lived and not a persistent logged-in desktop session.
5. **Messaging scope:** Telegram requires a bot token and webhook secret. Generic outgoing webhook delivery is supported for Slack/Discord or explicitly allowlisted HTTPS hosts. WhatsApp, email, Discord bot events, Slack event ingestion, and persistent channel polling are not implemented.
6. **MCP compatibility:** this is a minimal JSON-RPC HTTP endpoint, not a complete implementation of every MCP transport/version or OAuth flow.
7. **Research network pinning:** robust pinned-IP transport against DNS rebinding remains a hardening task.
8. **Restore workflow:** backup download exists; in-app restore/rollback is not implemented.
9. **Production operations:** no multi-user tenancy, roles/permissions, secret vault, distributed scheduler, job retry policy, or audit-grade authorization.
10. **Verification:** run `python -m pip install -e ".[test]"` and `python -m pytest -q`; confirm GitHub Actions before release. This change set has not been represented as runtime-tested unless a CI result confirms it.

## Security and recovery checklist

- Keep `NANO_HOST=127.0.0.1` unless remote access is intentional.
- Set a strong `NANO_API_TOKEN` before remote binding; configure TLS and firewall rules too.
- Keep `NANO_LITERT_URL` on loopback.
- Review scheduled prompts and skill proposals before enabling them.
- Require explicit approval for terminal/browser actions.
- Treat imported web pages and model output as untrusted.
- Download backups regularly and verify them with `PRAGMA integrity_check`.
