# Security

Nano AI is local-first by default.

- Nano binds to `127.0.0.1` by default; LiteRT-LM also defaults to loopback.
- Set a strong `NANO_API_TOKEN` before any LAN, reverse-proxy, or public exposure. Requests use `Authorization: Bearer <token>` or `X-Nano-Token`.
- The CLI refuses non-loopback binds when `NANO_API_TOKEN` is missing. Requests from non-loopback peers are rejected without a token. Use TLS and a firewall/reverse proxy for remote access.
- A configured token protects API and MCP endpoints; the web UI asks for it and retains it only in the current browser tab's session storage.
- Never commit secrets. Configure Telegram credentials and webhook secrets through environment variables.
- MCP exposes only the enabled built-in allowlisted tools; it does not expose arbitrary Python execution.
- The terminal runner never invokes a shell. It exposes a fixed set of read-oriented commands, validates relative paths, bounds output, and requires explicit approval for each run.
- Browser automation is optional, host-allowlisted, and requires explicit approval for click/fill actions. By default it can inspect localhost only.
- Desktop control is disabled unless `NANO_ENABLE_DESKTOP_CONTROL=true`; screenshot is read-only, while click/type/key actions require explicit approval and use a small key/coordinate allowlist.
- Outbound webhooks require HTTPS and a host allowlist. Add custom hosts through `NANO_WEBHOOK_ALLOWED_HOSTS`.
- Scheduled jobs execute user-authored assistant prompts, not arbitrary shell commands. Review jobs and run history.
- Model import cancellation terminates the child process; progress is best-effort. If LiteRT-LM does not emit a percentage, the UI labels progress as an estimate.
- Web research content and imported knowledge are untrusted reference text, never executable instructions.
- No Firebase or mandatory cloud AI provider is required. Telegram/webhook delivery requires internet access and configured credentials.
- Voice audio remains local when Vosk/Piper are configured.

Keep Nano and LiteRT-LM on loopback unless remote access is intentional and authenticated. Do not treat an API token as a substitute for TLS, firewall rules, and operational review.
