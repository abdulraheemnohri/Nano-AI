from nano.mcp import handle_message


def test_jsonrpc_notification_without_id_has_no_response():
    assert handle_message({"jsonrpc": "2.0", "method": "ping"}) is None


def test_jsonrpc_request_with_id_still_returns_response():
    response = handle_message({"jsonrpc": "2.0", "id": 17, "method": "ping"})

    assert response == {"jsonrpc": "2.0", "id": 17, "result": {}}
