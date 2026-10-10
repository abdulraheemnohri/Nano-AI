# Nano AI — Complete Installation and Operations Guide

This guide covers supported installation routes, optional dependencies, first-run setup, daily operation, diagnostics, and automatic startup. It describes the checked-in project rather than promising integrations that are not implemented.

## 1. What gets installed

Nano AI is a local-first, single-user assistant with a Python CLI, FastAPI backend, embedded HTML/CSS/JavaScript UI, and SQLite persistence. Core Python dependencies are declared in `pyproject.toml`; `requirements.txt` installs the project and its core dependencies. Optional voice, browser, desktop, and test dependencies are separate.

**LiteRT-LM and the model are separate from the Nano Python package.** The default model artifact is about 932 MB, before runtime overhead and other files. Check free disk space and device memory before downloading it. Model import needs an internet connection; inference can be local after the runtime and model are installed.

Current boundaries: the scheduler is a single-process worker; specialist agents are role prompts using the configured model; feedback updates local context, not model weights; optional integrations need host-specific verification. See [A-to-Z audit](A_TO_Z_AUDIT.md) and [final release review](FINAL_RELEASE_REVIEW.md).

## 2. Requirements

- Python 3.10 or newer; CI currently tests Python 3.12.
- Git for the source-checkout method.
- Internet during package/model downloads; internet is not required for ordinary local inference once dependencies and model files are present, except for features explicitly using web research or messaging.
- A supported LiteRT-LM CLI installation. LiteRT-LM support and performance depend on OS, architecture, Python version, and the upstream runtime release.
- Enough storage for Python packages, the model, and SQLite data. The default model artifact is about 932 MB; leave additional free space.
- Optional Node.js is useful for checking UI JavaScript during development; it is not needed to run the packaged UI.

Do not assume that a successful Python package install means LiteRT-LM inference works on every computer. Run `nano-ai doctor` and do an actual chat smoke test.

## 3. Installation method A — clone the source (Linux, macOS, Windows)

### Debian / Ubuntu

Install system tools and Python venv support:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
git clone https://github.com/abdulraheemnohri/Nano-AI.git
cd Nano-AI
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -U litert-lm
nano-ai init
nano-ai doctor
```

If your distribution separates venv support into a versioned package, install the matching `python3-venv` package. Do not run the app with `sudo`; run it as your normal user so its local data remains owned by you.

### macOS

Install Git and Python 3.10+ (for example through your preferred package manager), then:

```bash
git clone https://github.com/abdulraheemnohri/Nano-AI.git
cd Nano-AI
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -U litert-lm
nano-ai init
nano-ai doctor
```

The Nano package may install even if a compatible LiteRT-LM runtime is not available for your macOS/CPU combination. Verify upstream LiteRT-LM support before relying on inference.

### Windows PowerShell

Install Git and Python 3.10+ and ensure Python is on PATH. Then:

```powershell
git clone https://github.com/abdulraheemnohri/Nano-AI.git
Set-Location Nano-AI
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -U litert-lm
nano-ai init
nano-ai doctor
```

If PowerShell blocks activation, use a permitted execution-policy setting for the current user/session or call the virtual-environment executable directly (for example `.\.venv\Scripts\nano-ai.exe doctor`). Do not weaken machine-wide security policy just for activation.

## 4. Installation method B — optional features

The package's authoritative dependency declarations are in `pyproject.toml`. Use the matching extras when you need optional features:

```bash
python -m pip install -e ".[voice]"
python -m pip install -e ".[browser]"
python -m pip install -e ".[desktop]"
python -m pip install -e ".[test]"
python -m pip install -e ".[voice,browser,desktop,test]"
```

On Windows, use the same quoted extra strings in PowerShell. You may instead use the repository's requirements files:

- `requirements.txt` — core project.
- `requirements-voice.txt` — core project plus Vosk, sounddevice, and Piper TTS.
- `requirements-browser.txt` — core project plus Playwright.
- `requirements-desktop.txt` — core project plus PyAutoGUI and Pillow.
- `requirements-test.txt` — core project plus pytest and HTTPX.
- `requirements-all.txt` — core project plus all optional groups above.

For browser automation, install the Playwright browser binary only if you use that feature and follow Playwright's official installation guidance for your OS. Voice features also require compatible local voice assets and audio devices; Python packages alone do not supply every voice/model asset. Desktop controls are opt-in and approval-gated.

## 5. Installation method C — install a built wheel

This route is for a wheel downloaded from a trusted project release or built from a checkout. A release must actually exist before you can download its artifacts; do not assume an unreleased version is published.

Build locally from the source checkout:

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
python -m pip install dist/nano_ai-*.whl
nano-ai --help
nano-ai doctor
```

If shell wildcard expansion or wheel filenames differ on your platform, specify the exact wheel path. Install LiteRT-LM separately if supported on the target platform. A wheel installation does not include the model weights or runtime model registry.

## 6. First run and local inference

After the package install:

```bash
nano-ai init
nano-ai doctor
nano-ai download-model
```

The model import uses the project's configured LiteRT-LM CLI operation and downloads the default Qwen3 1.7B artifact. It requires internet access and disk space. If import fails, read the exact CLI error and check the installed runtime's `litert-lm --help`; do not guess or paste commands from a different LiteRT-LM version.

Start the model server in terminal 1:

```bash
nano-ai litert-lm
```

Start the Nano web application in terminal 2, from the same virtual environment:

```bash
nano-ai web
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The local model endpoint defaults to `http://127.0.0.1:9379`. Keep both endpoints on loopback unless you have intentionally configured authentication, TLS, firewall rules, and a safe reverse proxy.

Useful commands:

```bash
nano-ai --help
nano-ai status
nano-ai model
nano-ai models
nano-ai doctor
python -m pytest -q
```

## 7. How Nano AI works after installation

1. **CLI / Web UI:** the `nano-ai` command initializes data, reports status, starts services, and runs diagnostics. The browser UI is packaged in `nano/static/`.
2. **API:** FastAPI routes validate requests and connect the UI to chat, memory, learning, skills, tools, research, settings, scheduler, model setup, and system-health functions.
3. **Inference:** Nano sends model requests to the LiteRT-LM local OpenAI-compatible endpoint. The LiteRT-LM server and model must be available independently.
4. **Persistence:** SQLite stores conversations, memories, settings, learning records, jobs, and related local state. Protect and back up the database; it may contain private conversations.
5. **Tools and automation:** built-in tools are allowlisted. Optional terminal/browser/desktop actions are bounded and approval-gated. Scheduled work runs in the Nano process and stops when that process stops.
6. **Learning / Self-X:** explicit feedback, lessons, goals, plans, and research provenance are stored locally. Improvement and skill proposals require review; this is not automatic model-weight training.
7. **Diagnostics and recovery:** `nano-ai doctor` and the System health panel report conditions. They do not silently repair the database or restart arbitrary system processes.

## 8. Automatic startup — Linux systemd user services

This is the built-in automatic-start method. Complete the normal install, install LiteRT-LM, initialize Nano, and import the model first. Then run as your normal user:

```bash
nano-ai install-user-service
systemctl --user status nano-ai.service nano-ai-litert-lm.service
journalctl --user -u nano-ai.service -f
```

The command creates/enables user-level systemd units for the LiteRT-LM server and Nano web app. They start at user login, not necessarily before login. Verify both services and the web UI after installing; inspect logs if either fails. Service behavior depends on the paths and environment available to the user service manager.

To make user services start at system boot even before an interactive login, an administrator can explicitly enable lingering:

```bash
sudo loginctl enable-linger "$USER"
```

This is an optional system-level decision and is not enabled automatically. To disable it later:

```bash
sudo loginctl disable-linger "$USER"
```

Remove the Nano-managed user services with:

```bash
nano-ai uninstall-user-service
```

Then inspect `systemctl --user status` to confirm they are gone. Keep the app bound to loopback for a single-machine setup.

## 9. Automatic startup — Windows and macOS

The repository currently provides a built-in service installer only for Linux systemd user services. On Windows and macOS, start manually in separate terminals using the commands above. If you choose to configure Windows Task Scheduler or macOS launchd yourself, configure two separate processes (LiteRT-LM and Nano web), use absolute paths to the virtual-environment executables, set the project/data working directory explicitly, run as your normal user, and capture logs. Verify the exact commands interactively before scheduling them. No official Windows/macOS service installer is currently included; do not use Linux systemd commands on these platforms.

## 10. Configuration and data

Use the Settings page for supported application settings. Environment variables can override deployment values; see `.env.example` and `nano/config.py` for the current names and defaults. Do not commit tokens or private environment files.

Before remote binding, set a strong `NANO_API_TOKEN` and configure TLS/firewall/proxy protections. The app intentionally refuses an unauthenticated remote bind. Remote access is not recommended unless you understand the deployment risks.

Use the in-app backup endpoint or supported export flow and verify backups. Keep backups private. Practice restore and updater rollback against disposable data before relying on recovery in a real environment.

## 11. Troubleshooting checklist

- **`nano-ai: command not found`:** activate `.venv`, or invoke the executable under `.venv/bin/` (Linux/macOS) or `.venv\Scripts\` (Windows).
- **`litert-lm not found`:** install it in the same Python environment where supported, then check `litert-lm --help`.
- **UI loads but chat fails:** run `nano-ai doctor`, check `nano-ai litert-lm`, then inspect the model endpoint and registry.
- **Port already in use:** do not start a duplicate service; inspect the process listening on 8000 or 9379 and confirm it is the expected service.
- **Model import fails:** verify repository/artifact names against the installed LiteRT-LM version, connectivity, free disk space, and logs.
- **Voice/browser/desktop is unavailable:** install only the matching extra, platform prerequisites, browser binary or voice assets, and grant OS permissions where needed.
- **Service starts then exits:** inspect `journalctl --user -u nano-ai.service -n 100 --no-pager` and `journalctl --user -u nano-ai-litert-lm.service -n 100 --no-pager`; run `nano-ai doctor` interactively under the same account.
- **Need to update:** back up first, review changes, use the explicit System-page update flow or a clean Git workflow, install dependency changes manually, and restart services manually when required.

## 12. Verification before relying on the installation

```bash
python -m pip install -e ".[test]"
python -m pytest -q
nano-ai doctor
```

Then verify real inference, chat history, memory save/search/forget, settings, API authentication, model import/cancellation, scheduler retry/restart recovery, and backup/restore. Test voice/browser/desktop only if you plan to use them. CI is not a substitute for testing LiteRT-LM on your actual device.

## Scope statement

Nano AI is intended as a local-first, single-user assistant with bounded automation. This guide does not imply production certification, unrestricted shell execution, a distributed agent swarm, native WhatsApp/email/Slack/Discord event ingestion, full MCP OAuth/transport coverage, or automatic model-weight training.
