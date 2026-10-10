"""Security boundary regression tests for API auth, approvals, and research URLs."""

import pytest
from fastapi.testclient import TestClient

from nano.app import app
from nano.research import _validate_public_url


def test_configured_api_token_is_required(monkeypatch):
    monkeypatch.setenv("NANO_API_TOKEN", "test-only-token")

    with TestClient(app) as client:
        denied = client.get("/api/tools")
        allowed = client.get("/api/tools", headers={"Authorization": "Bearer test-only-token"})

    assert denied.status_code == 401
    assert allowed.status_code == 200


def test_terminal_api_rejects_unapproved_actions(monkeypatch):
    monkeypatch.setenv("NANO_API_TOKEN", "test-only-token")

    with TestClient(app) as client:
        response = client.post(
            "/api/terminal/run",
            headers={"Authorization": "Bearer test-only-token"},
            json={"command": "pytest", "args": [], "approved": False},
        )

    assert response.status_code == 403
    assert "approval" in response.json()["detail"].lower()


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/",
        "https://127.0.0.1/",
        "https://localhost/",
        "https://example.com:444/",
        "https://user:password@example.com/",
    ],
)
def test_research_rejects_non_public_or_nonstandard_urls(url):
    with pytest.raises(ValueError):
        _validate_public_url(url)

def test_forwarded_remote_requests_require_token_even_on_loopback_bind(monkeypatch):
    from nano import config
    monkeypatch.setattr(config, "HOST", "127.0.0.1")
    monkeypatch.setenv("NANO_API_TOKEN", "")
    with TestClient(app) as client:
        response = client.get("/api/tools", headers={"X-Forwarded-For": "203.0.113.10"})
    assert response.status_code == 503
    assert "NANO_API_TOKEN" in response.json()["detail"]
