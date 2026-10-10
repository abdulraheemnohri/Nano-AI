# Nano AI — Complete Installation and Operation Guide

Nano AI is a local-first Python assistant. The application, database, voice processing, and browser automation run locally; internet access is needed for initial package/model downloads and optional web research. The default model is the 4B LiteRT-LM artifact listed below. No Firebase, Docker, or paid cloud AI API is required.

## 1. Requirements

- Python 3.10+ and Git.
- Recommended: 8 GB RAM or more and at least 5 GB free disk for the model plus voice/browser assets. The 4B model file is about 2.1 GB and can use several GB RAM; 6 GB systems may be constrained.
- Linux, macOS, or Windows for the Python app; the Linux boot-service command requires systemd.
- Internet during setup; after model and optional voice/browser assets are installed, basic local chat and offline voice can work without internet.
- Browser automation uses Playwright Chromium. Desktop control is a separate optional feature and remains disabled unless explicitly enabled.

## 2. Install from source (Linux / Debian / Ubuntu / macOS)

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

On Debian/Ubuntu, if Python reports that venv is missing, install the OS package first: `sudo apt update && sudo apt install -y python3-venv python3-pip git`. Do not run the project with sudo.

## 3. Windows PowerShell

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

If script activation is blocked by policy, use the venv executable directly: `.\.venv\Scripts\python.exe -m pip install -e .` and `.\.venv\Scripts\nano-ai.exe doctor`. Keep using the same environment for every command.

## 4. Install from a built wheel (advanced / offline transfer)

On an internet-connected build machine, create a wheel with `python -m pip install build && python -m build`, then transfer `dist/nano_ai-*.whl` to the target. On the target, install it with `python -m pip install /path/to/nano_ai-*.whl` and install `litert-lm` separately. Optional extras need a compatible wheel set or internet access. This project also supports the standard editable/source install above; there is no verified standalone one-click OS installer yet.

## 5. Download and select the default Qwen3 4B model

```bash
nano-ai download-model
litert-lm list
nano-ai model
```

The default import is:

```bash
litert-lm import --from-huggingface-repo=litert-community/Qwen3-4B-Thinking-2507 Qwen3_4b_thinking_dynamic_wi4b32_afp32.litertlm qwen3-4b-thinking-2507
```

The model artifact is about 2.1 GB; keep at least 3 GB free before import. This model is a reasoning model: generation may take longer and should usually allow at least 2048 output tokens. Exact performance depends on CPU/GPU backend and available RAM.

## 6. Start the assistant

Terminal 1 — local model API:

```bash
nano-ai litert-lm
```

Terminal 2 — Nano web application:

```bash
nano-ai web
```

Open http://127.0.0.1:8000. On first application startup, Nano automatically checks the LiteRT-LM registry and starts importing the default Qwen3 4B Thinking model in the background when it is missing. This is enabled by default, requires internet and at least 3 GB free disk space, and may use several GB RAM when running. The Model page displays status and cancellation. To opt out, open Settings and disable `auto_download_model`; you can still start import manually from Model. Use Talk to chat; Memory for saved memories; Learning for feedback/lessons; Skills for reviewed skills; Knowledge and Web Research for local knowledge and explicit web fetches; Model for runtime status/import; Automation & Agents for bounded scheduled prompts, specialist role prompts and approved browser actions; Settings for talk style, speech and background checks; System for health, logs/status and backup/update tools.

Check `nano-ai status`, `nano-ai model`, and `nano-ai doctor` if chat is not working. Confirm the served ID from `litert-lm list` and `http://127.0.0.1:9379/v1/models`.

## 7. Automatically install local voice and browser support

From the activated project virtual environment, run:

```bash
nano-ai setup-extras
```

This opt-in command installs the project's voice/browser extras, installs the Playwright Chromium browser, downloads a small English Vosk speech-recognition model, and downloads the English US Piper Lessac medium voice and metadata into the local `models/` directory. It may download several hundred MB and requires internet; run it only if you want these features. It is safe to rerun and skips existing valid assets. It does not enable desktop control or grant browser actions approval.

Voice defaults are local:
- Vosk STT model: `models/vosk-model-small-en-us-0.15`
- Piper TTS voice: `models/piper/en_US-lessac-medium.onnx`
- Playwright Chromium: installed in Playwright's browser cache.

After setup, restart Nano. In Settings enable voice and Auto TTS if desired; grant microphone permission to the local web page. Browser actions remain host-allowlisted and click/fill actions require explicit approval. The default voice assets are English; select a different compatible Vosk/Piper voice manually if you need Urdu or another language.

Manual alternatives:
- Voice packages: `python -m pip install -e ".[voice]"`
- Browser packages: `python -m pip install -e ".[browser]" && python -m playwright install chromium`
- Combined requirements file: `python -m pip install -r requirements-full.txt`

## 8. Automatic background running and Linux startup

Start both processes manually using the two terminals above. On Linux with systemd, after the model is imported, run:

```bash
nano-ai install-user-service
systemctl --user status nano-ai.service nano-ai-litert-lm.service
journalctl --user -u nano-ai.service -f
```

The user services start at login and restart on failure. For boot-before-login operation, explicitly enable lingering (this is a system-level decision):

```bash
sudo loginctl enable-linger "$USER"
```

To stop/uninstall the services:

```bash
nano-ai uninstall-user-service
```

This service installer is Linux/systemd only. On Windows use two PowerShell terminals or configure Task Scheduler yourself; on macOS use two terminals or a user LaunchAgent. No Windows/macOS autostart installer is claimed in this release. Do not enable autostart until model import and manual chat have worked.

## 9. Requirements files and dependencies

- `requirements.txt`: base project install.
- `requirements-voice.txt`: project plus optional Vosk/Piper and browser extras.
- `requirements-browser.txt`: project plus Playwright.
- `requirements-full.txt`: project plus voice, browser, desktop and test extras.

Core Python dependencies are declared in `pyproject.toml`: FastAPI, Uvicorn, and python-multipart. Optional extras are declared there too, so avoid maintaining duplicate pinned package lists. LiteRT-LM is installed separately because the project talks to its CLI and CLI releases/platform support can evolve independently. Playwright browser binaries are installed separately from the Python package.

## 10. Verify, use, and troubleshoot

```bash
nano-ai doctor
nano-ai status
nano-ai model
python -m pip install -e ".[test]"
python -m pytest -q
```

- CLI missing: activate the virtual environment again.
- Model import fails: check internet, disk space, Hugging Face artifact name and LiteRT-LM CLI version.
- Out of memory: close other apps or switch explicitly to a smaller compatible model.
- Server port busy: use `nano-ai litert-lm --port 9380` and set `NANO_LITERT_URL=http://127.0.0.1:9380` before starting Nano.
- Voice not ready: rerun `nano-ai setup-extras`, then inspect System health and confirm model paths.
- Browser not ready: run `python -m playwright install chromium` and review `NANO_BROWSER_ALLOWED_HOSTS`.
- Keep `NANO_HOST=127.0.0.1`; set a strong `NANO_API_TOKEN`, TLS, and firewall rules before remote access.



### systemd says `bad-setting` for `nano-ai.service`

Upgrade Nano AI to a revision containing the systemd user-unit compatibility fix, activate the same virtual environment used for installation, then reinstall the units:

```bash
source .venv/bin/activate
python -m pip install -e .
nano-ai install-user-service
systemctl --user daemon-reload
systemctl --user status nano-ai-litert-lm.service nano-ai.service
journalctl --user -u nano-ai.service -n 100 --no-pager
```

If it still fails, collect the exact parser diagnostic before changing settings:

```systemd-analyze --user verify ~/.config/systemd/user/nano-ai.service ~/.config/systemd/user/nano-ai-litert-lm.service
systemctl --user show nano-ai.service -p LoadState -p FragmentPath
systemctl --user cat nano-ai.service
```

The installer now validates that the user manager loaded each unit before enabling it. The unit files intentionally avoid `PrivateTmp=`, which is not supported in some user-manager configurations and can result in `bad-setting`.

## 11. Local data and offline mode

The SQLite database defaults to `data/nano.sqlite3`; models live under `models/`. Back up this data because it contains conversation history, memories, and imported knowledge. After setup, chat and speech processing are local; browser research, Hugging Face downloads, messaging webhooks, and other internet integrations naturally require network access.
