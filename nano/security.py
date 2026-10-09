"""Authentication and request protection helpers."""
import hmac
import ipaddress
import os
import threading
import time
from collections import deque
from . import config

_RATE_LOCK = threading.Lock()
_RATE_BUCKETS = {}
_RATE_WINDOW_SECONDS = 60


def configured_token():
    return os.getenv("NANO_API_TOKEN", "").strip()


def is_loopback_host(host=None):
    host = (host or config.HOST).strip().lower().strip("[]")
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


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


def max_request_bytes():
    try:
        return max(16_384, min(int(os.getenv("NANO_MAX_REQUEST_BYTES", "1048576")), 10_000_000))
    except ValueError:
        return 1_048_576


def rate_limit_per_minute():
    try:
        return max(10, min(int(os.getenv("NANO_RATE_LIMIT_PER_MINUTE", "120")), 10_000))
    except ValueError:
        return 120


def request_rate_allowed(client_key, now=None):
    """Simple per-process API request limit; use a proxy limit for multi-worker deployments."""
    now = time.monotonic() if now is None else now
    limit = rate_limit_per_minute()
    cutoff = now - _RATE_WINDOW_SECONDS
    with _RATE_LOCK:
        bucket = _RATE_BUCKETS.setdefault(str(client_key or "unknown"), deque())
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        if len(_RATE_BUCKETS) > 4096:
            for key in list(_RATE_BUCKETS)[:1024]:
                if not _RATE_BUCKETS[key] or _RATE_BUCKETS[key][-1] <= cutoff:
                    _RATE_BUCKETS.pop(key, None)
        return True
