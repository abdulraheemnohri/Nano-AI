from nano import config
from nano.service import build_user_units


def test_user_service_units_are_loopback_only_and_restart_on_failure(monkeypatch):
    monkeypatch.setattr(config, "HOST", "127.0.0.1")
    monkeypatch.setattr(config, "LITERT_URL", "http://127.0.0.1:9379")
    units = build_user_units("/opt/nano venv/bin/nano-ai", "/opt/litert-lm")
    assert set(units) == {"nano-ai.service", "nano-ai-litert-lm.service"}
    assert "Restart=on-failure" in units["nano-ai.service"]
    assert "serve --host 127.0.0.1 --port 9379" in units["nano-ai-litert-lm.service"]
    assert 'WorkingDirectory="' in units["nano-ai.service"]


def test_user_service_builder_rejects_remote_bind(monkeypatch):
    monkeypatch.setattr(config, "HOST", "0.0.0.0")
    monkeypatch.setattr(config, "LITERT_URL", "http://127.0.0.1:9379")
    import pytest
    with pytest.raises(RuntimeError, match="loopback-only"):
        build_user_units("/usr/bin/nano-ai", "/usr/bin/litert-lm")
