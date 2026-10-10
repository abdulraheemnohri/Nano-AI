from fastapi import Response

from nano import app as app_module


def test_mcp_notification_returns_bodyless_202(monkeypatch):
    monkeypatch.setattr(app_module, "handle_message", lambda message: None)

    response = app_module.mcp_endpoint(
        {"jsonrpc": "2.0", "method": "notifications/initialized"}
    )

    assert isinstance(response, Response)
    assert response.status_code == 202
    assert response.body == b""
