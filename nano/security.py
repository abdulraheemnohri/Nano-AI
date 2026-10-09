"""Authentication helpers for local and remote Nano API deployments."""
import hmac
import os
from . import config

def configured_token():
    return os.getenv("NANO_API_TOKEN", "").strip()

def is_loopback_host(host=None):
    host = (host or config.HOST).strip().lower()
    return host in {"127.0.0.1", "localhost", "::1"}

def auth_policy():
    token = configured_token()
    remote = not is_loopback_host()
    return {"token_configured": bool(token), "remote_host": remote,
            "authentication_required": bool(token) or remote}

def authorized(provided):
    expected = configured_token()
    if not expected:
        return is_loopback_host()
    return bool(provided) and hmac.compare_digest(provided, expected)
