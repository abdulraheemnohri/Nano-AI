import pytest

from nano import agents, desktop, mcp, security, terminal
from nano.scheduler import create_job


def test_auth_token_uses_constant_time_comparison(monkeypatch):
    monkeypatch.setenv("NANO_API_TOKEN", "correct-horse-battery")
    assert security.authorized("correct-horse-battery")
    assert not security.authorized("wrong")


def test_loopback_hosts_are_recognized():
    assert security.is_loopback_host("127.0.0.1")
    assert security.is_loopback_host("localhost")
    assert not security.is_loopback_host("0.0.0.0")


def test_terminal_rejects_arbitrary_commands():
    with pytest.raises(ValueError):
        terminal.run_command("rm", ["-rf", "/"])
    with pytest.raises(ValueError):
        terminal.run_command("ls", ["../../etc"])


def test_mcp_tools_list_uses_json_rpc(tmp_path, monkeypatch):
    import nano.config as cfg
    import nano.db as dbm
    db = tmp_path / "mcp.sqlite3"
    monkeypatch.setattr(cfg, "DB_PATH", db)
    monkeypatch.setattr(dbm, "DB_PATH", db)
    dbm.init_db()
    result = mcp.handle_message({"jsonrpc":"2.0","id":7,"method":"tools/list","params":{}})
    assert result["id"] == 7
    assert result["result"]["tools"]
    assert all("name" in item and "inputSchema" in item for item in result["result"]["tools"])


def test_mcp_unknown_method_returns_method_not_found():
    result = mcp.handle_message({"jsonrpc":"2.0","id":2,"method":"made-up"})
    assert result["error"]["code"] == -32601


def test_agent_role_validation_happens_before_model_work():
    with pytest.raises(ValueError):
        agents.delegate("unknown-role", "test")


def test_scheduler_rejects_unbounded_job_types_and_intervals():
    with pytest.raises(ValueError):
        create_job("bad", "shell", {"prompt":"do things"}, 60)
    with pytest.raises(ValueError):
        create_job("bad", "assistant_prompt", {"prompt":"hello"}, 1)


def test_desktop_control_is_disabled_by_default(monkeypatch):
    monkeypatch.setenv("NANO_ENABLE_DESKTOP_CONTROL", "false")
    with pytest.raises(PermissionError):
        desktop.desktop_action("click", x=1, y=1, approved=True)


def test_api_requires_configured_token(tmp_path, monkeypatch):
    import nano.config as cfg
    import nano.db as dbm
    from fastapi.testclient import TestClient
    from nano.app import app
    db = tmp_path / "auth.sqlite3"
    monkeypatch.setattr(cfg, "DB_PATH", db)
    monkeypatch.setattr(dbm, "DB_PATH", db)
    monkeypatch.setenv("NANO_API_TOKEN", "test-secret-token")
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 401
        response = client.get("/api/health", headers={"Authorization":"Bearer test-secret-token"})
        assert response.status_code == 200


def test_voice_upload_can_exceed_default_json_body_limit_and_is_streamed(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import nano.app as app_module
    import nano.config as cfg
    import nano.db as dbm

    database = tmp_path / "voice-upload.sqlite3"
    monkeypatch.setattr(cfg, "DB_PATH", database)
    monkeypatch.setattr(dbm, "DB_PATH", database)
    monkeypatch.delenv("NANO_API_TOKEN", raising=False)
    monkeypatch.setattr(app_module, "transcribe_wav", lambda path: "recognized")
    payload = b"RIFF" + b"x" * (1536 * 1024)

    with TestClient(app_module.app) as client:
        response = client.post(
            "/api/voice/stt",
            files={"file": ("sample.wav", payload, "audio/wav")},
        )

    assert response.status_code == 200
    assert response.json() == {"text": "recognized"}
    assert not list(tmp_path.glob("nano-stt-*"))

def test_request_size_and_rate_protection_are_configurable(monkeypatch):
    monkeypatch.setenv("NANO_MAX_REQUEST_BYTES", "32768")
    monkeypatch.setenv("NANO_RATE_LIMIT_PER_MINUTE", "10")
    assert security.max_request_bytes() == 32768
    assert security.rate_limit_per_minute() == 10


def test_rate_limit_blocks_after_configured_number(monkeypatch):
    monkeypatch.setenv("NANO_RATE_LIMIT_PER_MINUTE", "10")
    key = "test-rate-limit-unique"
    for i in range(10):
        assert security.request_rate_allowed(key, now=100+i*0.01)
    assert not security.request_rate_allowed(key, now=101)
