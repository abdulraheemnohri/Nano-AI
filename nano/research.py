"""Bounded web research for Nano AI. Web text is untrusted and never executed."""
import http.client
import ipaddress
import re
import socket
import ssl
import urllib.parse
from html.parser import HTMLParser

from .knowledge import ingest

MAX_PAGE_BYTES = 1_500_000
MAX_TEXT_CHARS = 100_000
USER_AGENT = "NanoAI-LocalResearch/1.0"


class _TextExtractor(HTMLParser):
    BLOCKED = {"script", "style", "noscript", "svg", "canvas", "nav", "footer", "header", "form"}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.blocked_tags = []
        self.title = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCKED:
            self.blocked_tags.append(tag)
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in self.BLOCKED and tag in self.blocked_tags:
            # Remove the matching blocked element without unblocking its parent.
            index = len(self.blocked_tags) - 1 - self.blocked_tags[::-1].index(tag)
            self.blocked_tags.pop(index)
        if tag == "title":
            self.in_title = False
        if tag in {"p", "div", "br", "li", "h1", "h2", "h3", "article", "section"}:
            self.parts.append("\n")

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        if self.in_title:
            self.title.append(text)
        if not self.blocked_tags:
            self.parts.append(text)


def _validate_public_url(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only public HTTPS URLs are allowed.")
    try:
        if parsed.port not in (None, 443):
            raise ValueError("Only standard HTTPS port 443 is allowed.")
    except ValueError as exc:
        raise ValueError("Invalid URL port.") from exc
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local") or not host:
        raise ValueError("Local and private hosts are blocked.")
    addresses = _resolve_public_addresses(host)
    if not addresses:
        raise ValueError("Could not resolve the public website host.")
    return parsed


def _resolve_public_addresses(host):
    """Resolve once, reject mixed/public-private answers, and return pinned IPs."""
    try:
        literal = ipaddress.ip_address(host)
        addresses = [literal]
    except ValueError:
        try:
            records = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            addresses = [ipaddress.ip_address(item[4][0].split("%", 1)[0]) for item in records]
        except (OSError, ValueError, IndexError) as exc:
            raise ValueError("Could not resolve the public website host.") from exc
    unique = list(dict.fromkeys(addresses))
    if not unique or any(not address.is_global for address in unique):
        raise ValueError("Private, loopback, and reserved network addresses are blocked.")
    return unique


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to a previously validated IP while retaining hostname TLS verification."""
    def __init__(self, hostname, address, timeout=12):
        super().__init__(hostname, 443, timeout=timeout, context=ssl.create_default_context())
        self._pinned_address = str(address)
        self._tls_hostname = hostname

    def connect(self):
        raw = socket.create_connection((self._pinned_address, 443), self.timeout, self.source_address)
        self.sock = self._context.wrap_socket(raw, server_hostname=self._tls_hostname)


def _open(url, timeout=12):
    current = url
    response = None
    for redirect_count in range(6):
        parsed = _validate_public_url(current)
        hostname = parsed.hostname.lower().rstrip(".")
        addresses = _resolve_public_addresses(hostname)
        address = addresses[0]
        path = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        connection = _PinnedHTTPSConnection(hostname, address, timeout=timeout)
        try:
            connection.request("GET", path, headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,text/plain",
                "Host": hostname,
                "Connection": "close",
            })
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                response.read(4096)
                connection.close()
                if not location:
                    raise ValueError("Redirect response did not include a location.")
                if redirect_count >= 5:
                    raise ValueError("Too many redirects.")
                current = urllib.parse.urljoin(current, location)
                continue
            if response.status < 200 or response.status >= 300:
                response.read(4096)
                raise RuntimeError(f"Web request returned HTTP {response.status}.")
            final_url = current
            content_type = response.headers.get_content_type()
            charset = response.headers.get_content_charset() or "utf-8"
            if content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
                response.read(4096)
                raise ValueError("This page is not HTML or plain text.")
            data = response.read(MAX_PAGE_BYTES + 1)
            if len(data) > MAX_PAGE_BYTES:
                raise ValueError("Page is too large (limit 1.5 MB).")
            return final_url, content_type, data.decode(charset, errors="replace")
        except (OSError, ssl.SSLError, http.client.HTTPException, TimeoutError) as exc:
            raise RuntimeError(f"Web request failed: {exc}") from exc
        finally:
            connection.close()
    raise ValueError("Too many redirects.")

