"""Explicit installer for Linux systemd user services."""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

from . import config


def _quote(value):
    value = str(value)
    if "\n" in value or "\r" in value:
        raise ValueError("Service values cannot contain newlines.")
    return '"' + value.replace("%", "%%").replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_user_units(nano_executable, litert_executable):
    host = config.HOST
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("The user-service installer supports loopback-only Nano binding. Configure NANO_HOST=127.0.0.1.")
    parsed = urlsplit(config.LITERT_URL)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("The user-service installer requires a local HTTP LiteRT-LM endpoint.")
    litert_host = parsed.hostname
    litert_port = parsed.port or 9379
    env = {
        "NANO_HOST": host,
        "NANO_PORT": str(config.PORT),
        "NANO_DATA_DIR": str(config.DATA_DIR),
        "NANO_MODEL_DIR": str(config.MODEL_DIR),
        "NANO_SKILLS_DIR": str(config.SKILLS_DIR),
        "NANO_DB": str(config.DB_PATH),
        "NANO_LITERT_URL": config.LITERT_URL,
        "NANO_LITERT_MODEL": config.LITERT_MODEL,
        "NANO_MODEL_NAME": config.MODEL_NAME,
        "NANO_MAX_CONTEXT": str(config.MAX_CONTEXT),
        "NANO_TEMPERATURE": str(config.TEMPERATURE),
        "NANO_LITERT_TIMEOUT": str(config.LITERT_TIMEOUT),
        "NANO_MAX_MESSAGE_CHARS": str(config.MAX_MESSAGE_CHARS),
        "NANO_LEARNING_ENABLED": "true" if config.LEARNING_ENABLED else "false",
        "NANO_STT_MODEL": config.STT_MODEL,
        "NANO_PIPER_COMMAND": config.PIPER_COMMAND,
        "NANO_PIPER_VOICE": config.PIPER_VOICE,
    }
    env_lines = "\n".join("Environment=" + _quote(k + "=" + v) for k, v in env.items())
    litert_unit = "\n".join([
        "[Unit]",
        "Description=Nano AI local LiteRT-LM model server",
        "After=network.target",
        "",
        "[Service]",
        "Type=simple",
        "ExecStart=" + _quote(litert_executable) + " serve --host " + litert_host + " --port " + str(litert_port),
        "Restart=on-failure",
        "RestartSec=5",
        "NoNewPrivileges=true",
        "UMask=0077",
        "",
        "[Install]",
        "WantedBy=default.target",
        "",
    ])
    nano_unit = "\n".join([
        "[Unit]",
        "Description=Nano AI local assistant web application",
        "After=network.target nano-ai-litert-lm.service",
        "Wants=nano-ai-litert-lm.service",
        "",
        "[Service]",
        "Type=simple",
        "WorkingDirectory=" + _quote(config.ROOT),
        env_lines,
        "ExecStart=" + _quote(nano_executable) + " web --host " + host + " --port " + str(config.PORT),
        "Restart=on-failure",
        "RestartSec=5",
        "NoNewPrivileges=true",

        "UMask=0077",
        "",
        "[Install]",
        "WantedBy=default.target",
        "",
    ])
    return {"nano-ai-litert-lm.service": litert_unit, "nano-ai.service": nano_unit}


def install_user_services():
    if not sys.platform.startswith("linux") or not shutil.which("systemctl"):
        raise RuntimeError("This command requires Linux with systemd.")
    manager = shutil.which("systemctl")
    nano_executable = shutil.which("nano-ai")
    litert_executable = shutil.which("litert-lm") or shutil.which("litert-lm.exe")
    if not nano_executable:
        raise RuntimeError("The nano-ai console script is not on PATH. Install the project with: pip install -e .")
    if not litert_executable:
        raise RuntimeError("LiteRT-LM is not installed or not on PATH. Install it before enabling boot services.")
    units = build_user_units(nano_executable, litert_executable)
    unit_dir = Path.home() / ".config" / "systemd" / "user"
    unit_dir.mkdir(parents=True, exist_ok=True)
    for name, content in units.items():
        path = unit_dir / name
        path.write_text(content, encoding="utf-8")
        path.chmod(0o600)
    subprocess.run([manager, "--user", "daemon-reload"], check=True)
    # Validate what the user manager actually loaded before enabling either unit.
    # This catches user-manager-only directives such as PrivateTmp= that can
    # make an otherwise plausible service file enter the bad-setting state.
    for name in units:
        result = subprocess.run(
            [manager, "--user", "show", "--property=LoadState", "--value", name],
            check=False, capture_output=True, text=True,
        )
        state = result.stdout.strip()
        if result.returncode != 0 or state != "loaded":
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                f"systemd did not load {name} correctly (LoadState={state or 'unknown'}). "
                f"Inspect with: systemctl --user status {name}; "
                f"systemd-analyze --user verify {unit_dir / name}. {detail}"
            )
    subprocess.run([manager, "--user", "enable", "--now", "nano-ai-litert-lm.service", "nano-ai.service"], check=True)
    return {"ok": True, "unit_dir": str(unit_dir), "services": list(units), "startup": "user login; enable systemd lingering separately for boot-before-login"}


def uninstall_user_services():
    if not sys.platform.startswith("linux") or not shutil.which("systemctl"):
        raise RuntimeError("This command requires Linux with systemd.")
    manager = shutil.which("systemctl")
    subprocess.run([manager, "--user", "disable", "--now", "nano-ai.service", "nano-ai-litert-lm.service"], check=False)
    unit_dir = Path.home() / ".config" / "systemd" / "user"
    removed = []
    for name in ("nano-ai.service", "nano-ai-litert-lm.service"):
        path = unit_dir / name
        if path.exists():
            path.unlink()
            removed.append(name)
    subprocess.run([manager, "--user", "daemon-reload"], check=True)
    return {"ok": True, "removed": removed}
