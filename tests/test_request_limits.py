"""Regression tests for request-size limits, including chunked HTTP requests."""

from fastapi.testclient import TestClient

from nano.app import app


def _chunks(payload: bytes, chunk_size: int = 4096):
    for start in range(0, len(payload), chunk_size):
        yield payload[start : start + chunk_size]


def test_chunked_mcp_request_over_limit_returns_413(monkeypatch):
    monkeypatch.setenv("NANO_API_TOKEN", "")
    monkeypatch.setenv("NANO_MAX_REQUEST_BYTES", "16384")
    payload = (
        b'{"jsonrpc":"2.0","id":1,"method":"ping","padding":"'
        + b"x" * 20_000
        + b'"}'
    )

    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            content=_chunks(payload),
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 413
    assert "size limit" in response.json()["detail"]


def test_chunked_mcp_request_within_limit_is_replayed_to_endpoint(monkeypatch):
    monkeypatch.setenv("NANO_API_TOKEN", "")
    monkeypatch.setenv("NANO_MAX_REQUEST_BYTES", "16384")
    payload = b'{"jsonrpc":"2.0","id":7,"method":"ping"}'

    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            content=_chunks(payload, 7),
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 200
    assert response.json() == {"jsonrpc": "2.0", "id": 7, "result": {}}
