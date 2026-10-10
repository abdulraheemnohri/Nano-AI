from nano import mcp


def test_initialize_without_params_uses_default_protocol_version():
    response = mcp.handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert response["result"]["protocolVersion"] == "2024-11-05"


def test_initialize_rejects_non_object_params_without_raising():
    for params in (None, [], "invalid", 12):
        response = mcp.handle_message(
            {"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": params}
        )
        assert response["error"]["code"] == -32602
        assert response["id"] == 2


def test_initialize_rejects_non_string_protocol_version():
    response = mcp.handle_message(
        {"jsonrpc": "2.0", "id": 3, "method": "initialize", "params": {"protocolVersion": 4}}
    )
    assert response["error"]["code"] == -32602


def test_tools_call_rejects_malformed_params_and_arguments(monkeypatch):
    monkeypatch.setattr(mcp, "run_tool", lambda *args: (_ for _ in ()).throw(AssertionError("must not run")))
    for params in (None, [], "invalid"):
        response = mcp.handle_message(
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": params}
        )
        assert response["error"]["code"] == -32602

    missing_name = mcp.handle_message(
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"arguments": {}}}
    )
    assert missing_name["error"]["code"] == -32602

    bad_arguments = mcp.handle_message(
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "calculator", "arguments": []}}
    )
    assert bad_arguments["error"]["code"] == -32602


def test_notifications_initialized_returns_no_response():
    assert mcp.handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
