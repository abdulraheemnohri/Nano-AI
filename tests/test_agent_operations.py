import pytest

from nano import agents, mcp, security, terminal
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
