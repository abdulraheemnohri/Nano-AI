from nano import config
from nano.service import build_user_units


def test_user_service_units_are_loopback_only_and_restart_on_failure(monkeypatch):
    monkeypatch.setattr(config, "HOST", "127.0.0.1")
    monkeypatch.setattr(config, "LITERT_URL", "http://127.0.0.1:9379")
    units = build_user_units("/opt/nano venv/bin/nano-ai", "/opt/litert-lm")
    assert set(units) == {"nano-ai.service", "nano-ai-litert-lm.service"}
    assert "Restart=on-failure" in units["nano-ai.service"]
    # PrivateTmp is not supported in many systemd user-manager contexts and
    # causes LoadState=bad-setting; keep user units portable.
    assert "PrivateTmp=" not in units["nano-ai.service"]
    assert "PrivateTmp=" not in units["nano-ai-litert-lm.service"]
    assert "NoNewPrivileges=true" in units["nano-ai.service"]
    assert "serve --host 127.0.0.1 --port 9379" in units["nano-ai-litert-lm.service"]
    assert 'WorkingDirectory="' in units["nano-ai.service"]


def test_user_service_builder_rejects_remote_bind(monkeypatch):
    monkeypatch.setattr(config, "HOST", "0.0.0.0")
    monkeypatch.setattr(config, "LITERT_URL", "http://127.0.0.1:9379")
    import pytest
    with pytest.raises(RuntimeError, match="loopback-only"):
        build_user_units("/usr/bin/nano-ai", "/usr/bin/litert-lm")


def test_installer_refuses_to_enable_bad_user_units(monkeypatch, tmp_path):
    import subprocess
    import pytest
    from nano import service

    monkeypatch.setattr(service.sys, "platform", "linux")
    monkeypatch.setattr(service.shutil, "which", lambda name: {
        "systemctl": "/usr/bin/systemctl",
        "nano-ai": "/venv/bin/nano-ai",
        "litert-lm": "/venv/bin/litert-lm",
    }.get(name))
    monkeypatch.setattr(service.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(config, "HOST", "127.0.0.1")
    monkeypatch.setattr(config, "LITERT_URL", "http://127.0.0.1:9379")

    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if "show" in args:
            return type("Result", (), {
                "returncode": 0, "stdout": "bad-setting\n",
                "stderr": "Invalid user service setting",
            })()
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(service.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="did not load nano-ai-litert-lm.service"):
        service.install_user_services()
    assert not any("enable" in args for args in calls)
