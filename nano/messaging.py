"""Optional outbound messaging adapters; credentials are environment-only."""
import http.client
import ipaddress
import json
import os
import socket
import ssl
from urllib.parse import urlparse, urlunsplit
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler
from urllib.error import URLError, HTTPError

MAX_RESPONSE_BYTES = 65536


def _post_json(url, payload, headers=None, timeout=15):
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})}, method="POST")

    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    try:
        with build_opener(NoRedirect).open(req, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1).decode("utf-8", "replace")
            return {"ok": 200 <= response.status < 300, "status_code": response.status,
                    "response": raw[:4000], "response_truncated": len(raw) > MAX_RESPONSE_BYTES}
    except (URLError, HTTPError, TimeoutError) as exc:
        raise RuntimeError("Messaging request failed: " + str(exc)[:500]) from exc


def telegram_send(chat_id, text):
    token = os.getenv("NANO_TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Set NANO_TELEGRAM_BOT_TOKEN to enable Telegram.")
    if not str(text).strip() or len(str(text)) > 4000:
        raise ValueError("Message must contain 1 to 4000 characters.")
    return _post_json(
        f"https://api.telegram.org/bot{token}/sendMessage",
        {"chat_id": str(chat_id), "text": str(text)},
    )


def _validate_webhook_url(url):
    parsed = urlparse(str(url))
    if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Webhook URL must be HTTPS and cannot include embedded credentials.")
    try:
        if parsed.port not in (None, 443):
            raise ValueError("Webhook URL must use standard HTTPS port 443.")
    except ValueError as exc:
        raise ValueError("Webhook URL has an invalid or unsupported port.") from exc
    if parsed.fragment:
        raise ValueError("Webhook URL cannot contain a fragment.")
    host = parsed.hostname.lower().rstrip(".")
    if not host:
        raise ValueError("Webhook hostname is required.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("IP-literal webhook hosts are not allowed.")

    allowed = {"hooks.slack.com", "discord.com", "discordapp.com"}
    allowed.update(
        item.strip().lower().rstrip(".")
        for item in os.getenv("NANO_WEBHOOK_ALLOWED_HOSTS", "").split(",")
        if item.strip()
    )
    if host not in allowed:
        raise ValueError("Webhook host is not allowlisted. Use Slack/Discord or add it to NANO_WEBHOOK_ALLOWED_HOSTS.")
    return parsed, host


def _resolve_public_webhook_address(host):
    """Resolve once, reject mixed/private answers, then pin the HTTPS socket to a public IP."""
    try:
        records = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        addresses = list(dict.fromkeys(ipaddress.ip_address(item[4][0].split("%", 1)[0]) for item in records))
    except (OSError, ValueError, IndexError) as exc:
        raise RuntimeError("Could not resolve the allowlisted webhook host.") from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("Webhook host resolved to a private, loopback, or reserved address.")
    return str(addresses[0])


class _PinnedWebhookConnection(http.client.HTTPSConnection):
    """Connect to a resolved IP while keeping TLS certificate checks bound to the hostname."""
    def __init__(self, hostname, address, timeout=15):
        super().__init__(hostname, 443, timeout=timeout, context=ssl.create_default_context())
        self._pinned_address = address
        self._tls_hostname = hostname

    def connect(self):
        raw = socket.create_connection((self._pinned_address, 443), self.timeout, self.source_address)
        self.sock = self._context.wrap_socket(raw, server_hostname=self._tls_hostname)


def webhook_send(url, text):
    if not str(text).strip() or len(str(text)) > 12000:
        raise ValueError("Message must contain 1 to 12000 characters.")
    parsed, host = _validate_webhook_url(url)
    address = _resolve_public_webhook_address(host)
    payload = {"content": str(text)} if host in {"discord.com", "discordapp.com"} else {"text": str(text)}
    data = json.dumps(payload).encode("utf-8")
    path = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
    connection = _PinnedWebhookConnection(host, address)
    try:
        connection.request("POST", path, body=data, headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(data)),
            "Host": host,
            "Connection": "close",
            "User-Agent": "NanoAI-Webhook/1.0",
        })
        response = connection.getresponse()
        raw = response.read(MAX_RESPONSE_BYTES + 1).decode("utf-8", "replace")
        return {
            "ok": 200 <= response.status < 300,
            "status_code": response.status,
            "response": raw[:4000],
            "response_truncated": len(raw) > MAX_RESPONSE_BYTES,
        }
    except (OSError, ssl.SSLError, http.client.HTTPException, TimeoutError) as exc:
        raise RuntimeError("Webhook request failed: " + str(exc)[:300]) from exc
    finally:
        connection.close()
