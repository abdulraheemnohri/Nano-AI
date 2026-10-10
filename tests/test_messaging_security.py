import socket

import pytest

from nano import messaging


@pytest.mark.parametrize(
    "url",
    [
        "http://hooks.slack.com/services/test",
        "https://hooks.slack.com:444/services/test",
        "https://127.0.0.1/services/test",
        "https://user:secret@hooks.slack.com/services/test",
        "https://hooks.slack.com/services/test#fragment",
        "https://attacker.example/services/test",
    ],
)
def test_webhook_url_rejects_unsafe_or_unapproved_urls(url, monkeypatch):
    monkeypatch.delenv("NANO_WEBHOOK_ALLOWED_HOSTS", raising=False)
    with pytest.raises(ValueError):
        messaging._validate_webhook_url(url)


def test_webhook_allowlist_normalizes_trailing_dot(monkeypatch):
    monkeypatch.delenv("NANO_WEBHOOK_ALLOWED_HOSTS", raising=False)
    parsed, host = messaging._validate_webhook_url("https://hooks.slack.com./services/test")
    assert host == "hooks.slack.com"
    assert parsed.path == "/services/test"


def test_webhook_custom_allowlist_is_supported(monkeypatch):
    monkeypatch.setenv("NANO_WEBHOOK_ALLOWED_HOSTS", "hooks.example.test.")
    parsed, host = messaging._validate_webhook_url("https://hooks.example.test/path")
    assert host == "hooks.example.test"


def test_webhook_dns_resolution_rejects_private_or_mixed_answers(monkeypatch):
    def fake_getaddrinfo(host, port, type):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
        ]

    monkeypatch.setattr(messaging.socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(ValueError, match="private"):
        messaging._resolve_public_webhook_address("hooks.slack.com")


def test_webhook_dns_resolution_returns_pinned_public_ip(monkeypatch):
    def fake_getaddrinfo(host, port, type):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]

    monkeypatch.setattr(messaging.socket, "getaddrinfo", fake_getaddrinfo)
    assert messaging._resolve_public_webhook_address("hooks.slack.com") == "93.184.216.34"


def test_webhook_send_uses_pinned_connection_and_reports_status(monkeypatch):
    monkeypatch.delenv("NANO_WEBHOOK_ALLOWED_HOSTS", raising=False)
    monkeypatch.setattr(messaging, "_resolve_public_webhook_address", lambda host: "93.184.216.34")
    captured = {}

    class FakeResponse:
        status = 204

        def read(self, limit):
            return b""

    class FakeConnection:
        def __init__(self, hostname, address):
            captured["hostname"] = hostname
            captured["address"] = address

        def request(self, method, path, body, headers):
            captured.update(method=method, path=path, body=body, headers=headers)

        def getresponse(self):
            return FakeResponse()

        def close(self):
            captured["closed"] = True

    monkeypatch.setattr(messaging, "_PinnedWebhookConnection", FakeConnection)
    result = messaging.webhook_send("https://hooks.slack.com/services/example", "hello")
    assert result["ok"] is True
    assert result["status_code"] == 204
    assert captured["address"] == "93.184.216.34"
    assert captured["headers"]["Host"] == "hooks.slack.com"
    assert captured["method"] == "POST"
    assert captured["closed"] is True


def test_webhook_send_rejects_blank_or_oversized_text(monkeypatch):
    monkeypatch.setattr(
        messaging, "_resolve_public_webhook_address",
        lambda host: (_ for _ in ()).throw(AssertionError("DNS should not run")),
    )
    with pytest.raises(ValueError):
        messaging.webhook_send("https://hooks.slack.com/services/example", "  ")
    with pytest.raises(ValueError):
        messaging.webhook_send("https://hooks.slack.com/services/example", "x" * 12001)
