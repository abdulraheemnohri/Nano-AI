# Nano AI A-to-Z Recheck — 2026-10-10

## Scope and evidence

This follow-up checks the merged Qwen3 4B default and install/voice/browser work from PR #36, along with release-facing docs, package metadata, model status reporting, and automated tests.

- Main commit under review: `c7b285032c0bd573a24b4a27753e56a22fc6a5ac`
- Main-branch CI: [run 38036864797](https://github.com/abdulraheemnohri/Nano-AI/actions/runs/38036864797) — Linux, Windows, macOS, and distribution build passed.
- Official model artifact: [Qwen3_4b_thinking_dynamic_wi4b32_afp32.litertlm](https://huggingface.co/litert-community/Qwen3-4B-Thinking-2507/blob/main/Qwen3_4b_thinking_dynamic_wi4b32_afp32.litertlm), 2,274,193,168 bytes (about 2.1 GB), 4096-token context. See the model card and manifest for the current backend caveats.

## Findings corrected in this follow-up

1. **Stale model references:** aligned the UI's custom import defaults, model prompts, package description, architecture/voice/user guides, and tests with Qwen3 4B-Thinking-2507.
2. **Incorrect artifact size:** corrected stale 932 MB / 1 GB claims to the actual 2.1 GB artifact size and at least 3 GB free-disk recommendation.
3. **Optional setup portability:** changed `nano-ai setup-extras` to install the declared optional packages directly instead of assuming an editable source checkout is available at runtime. This allows the setup command to work from installed-package layouts too.
4. **Model status clarity:** the Model API now distinguishes the LiteRT-LM registry model from an optional file at Nano's local model path; LiteRT-LM import manages a registry entry and should not be represented as copying the artifact into `models/`.
5. **Backend caveat:** documented the Hugging Face manifest's warning about the block-32 artifact on some GPU backends, including macOS Metal. Use CPU on macOS unless the exact device/runtime has been independently verified.
6. **Installer regression tests:** added tests for optional dependency installation, idempotent Piper asset setup, safe Vosk archive extraction, and path-traversal rejection.

## Installation contract

- Base Python dependencies are declared in `pyproject.toml`; `requirements.txt` points to the base project.
- `requirements-voice.txt` installs voice and browser Python extras; `requirements-browser.txt` installs Playwright; `requirements-full.txt` installs voice, browser, desktop, and test extras.
- LiteRT-LM is installed separately because the project uses its CLI as the local model runtime.
- `nano-ai setup-extras` is explicit and downloads English Vosk/Piper assets plus Playwright Chromium. It is not run silently on every startup.
- Linux systemd user services are supported. Windows/macOS built-in autostart installers are not currently implemented.
- The 4B model can need several GB RAM. Recommend 8 GB+; do not promise acceptable performance on every 6 GB system.

## Verification still required on real machines

CI is not a substitute for a real model smoke test. For each target OS/backend:

1. Install the exact release candidate into a clean virtual environment.
2. Run `nano-ai doctor` and `nano-ai init`.
3. Import the requested model and confirm the exact ID using `litert-lm list` and `/v1/models`.
4. Run a short inference that produces a final answer, not just a thinking prefix.
5. Run `nano-ai setup-extras`; verify microphone capture, Vosk transcription, Piper playback, and Chromium launch.
6. Verify Linux service start/stop, logs, and restart behavior on a disposable profile.
7. Confirm backup/restore and update/rollback only using disposable test data.

## Remaining limitations (not bugs that can be claimed fixed)

- The project is not production-certified or multi-tenant.
- No automatic model-weight training from user feedback.
- Specialist agents are bounded role prompts using the configured model, not a distributed model swarm.
- Scheduler/worker infrastructure is local and single-process, not a distributed queue.
- No unrestricted shell; browser/desktop interactions remain separately controlled and approval-gated.
- No complete MCP transport/OAuth implementation and no native WhatsApp/email/Slack/Discord event-ingestion adapters.
- Optional voice/browser dependencies, platform support, model inference, and GPU backend behavior need machine-specific validation.
- Stable release publication remains a separate tag-driven release action; passing CI does not itself publish a new version.
