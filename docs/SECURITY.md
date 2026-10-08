# Security

Nano AI is designed for local-first use.

- Default Nano host: `127.0.0.1`
- Default LiteRT-LM host: `127.0.0.1`
- No Firebase requirement.
- No mandatory cloud AI provider.
- No shell/terminal executor.
- No browser automation.
- No device-control agent.
- No arbitrary plugin execution.
- No silent model-weight training.
- Voice audio stays local when Vosk/Piper are configured.

If you expose either service to a LAN/public interface, add authentication, TLS and firewall controls. An unauthenticated local API should not be exposed publicly.
