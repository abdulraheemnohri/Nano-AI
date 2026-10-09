"""Bounded web research with public-IP pinning to resist DNS rebinding."""
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
            index = len(self.blocked_tags) - 1 - self.blocked_tags[::-1].index(tag)
            self.blocked_tags.pop(index)
        if tag == "title":
            self.in_title = False
        if tag in {"p", "div", "br", "li", "h1", "h2", "h3", "article", "section"}:
            self.parts.append("\\n")

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        if self.in_title:
            self.title.append(text)
        if not self.blocked_tags:
            self.parts.append(text)


def _resolve_public_addresses(host):
    """Resolve once and reject the whole hostname if any answer is non-public."""
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


def _validate_public_url(url, return_addresses=False):
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
    return (parsed, addresses) if return_addresses else parsed


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to a validated IP while verifying TLS against the original hostname."""

    def __init__(self, hostname, address, timeout=12):
        super().__init__(hostname, 443, timeout=timeout, context=ssl.create_default_context())
        self._pinned_address = str(address)
        self._tls_hostname = hostname

    def connect(self):
        raw = socket.create_connection((self._pinned_address, 443), self.timeout, self.source_address)
        self.sock = self._context.wrap_socket(raw, server_hostname=self._tls_hostname)


def _open(url, timeout=12):
    current = url
    for redirect_count in range(6):
        parsed, addresses = _validate_public_url(current, return_addresses=True)
        hostname = parsed.hostname.lower().rstrip(".")
        path = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        connection = _PinnedHTTPSConnection(hostname, addresses[0], timeout=timeout)
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
                if not location:
                    raise ValueError("Redirect response did not include a location.")
                if redirect_count >= 5:
                    raise ValueError("Too many redirects.")
                current = urllib.parse.urljoin(current, location)
                continue
            if response.status < 200 or response.status >= 300:
                response.read(4096)
                raise RuntimeError(f"Web request returned HTTP {response.status}.")
            content_type = response.headers.get_content_type()
            charset = response.headers.get_content_charset() or "utf-8"
            if content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
                response.read(4096)
                raise ValueError("This page is not HTML or plain text.")
            data = response.read(MAX_PAGE_BYTES + 1)
            if len(data) > MAX_PAGE_BYTES:
                raise ValueError("Page is too large (limit 1.5 MB).")
            return current, content_type, data.decode(charset, errors="replace")
        except (OSError, ssl.SSLError, http.client.HTTPException, TimeoutError) as exc:
            raise RuntimeError(f"Web request failed: {exc}") from exc
        finally:
            connection.close()
    raise ValueError("Too many redirects.")


def fetch_page(url):
    final_url, content_type, body = _open(url)
    if content_type == "text/plain":
        title = final_url
        text = body
    else:
        parser = _TextExtractor()
        parser.feed(body)
        title = " ".join(parser.title).strip() or final_url
        text = " ".join(" ".join(parser.parts).split())
    text = text[:MAX_TEXT_CHARS]
    if len(text) < 80:
        raise ValueError("Not enough readable text was found on this page.")
    return {"url": final_url, "title": title[:300], "text": text, "characters": len(text)}


def search_web(query, limit=8):
    query = " ".join(str(query).split())
    if not query or len(query) > 300:
        raise ValueError("Search query must contain 1-300 characters.")
    limit = max(1, min(int(limit), 10))
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    _, _, body = _open(url)

    class Results(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.items = []
            self.current = None
            self.capture = False

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            classes = attrs.get("class", "").split()
            if tag == "a" and "result__a" in classes:
                self.current = {"url": attrs.get("href", ""), "title": ""}
                self.capture = True

        def handle_data(self, data):
            if self.capture and self.current:
                self.current["title"] += data

        def handle_endtag(self, tag):
            if tag == "a" and self.capture and self.current:
                item = self.current
                item["title"] = item["title"].strip()
                href = item["url"]
                if href.startswith("//"):
                    href = "https:" + href
                elif href.startswith("/"):
                    href = urllib.parse.urljoin("https://html.duckduckgo.com", href)
                parsed = urllib.parse.urlparse(href)
                if parsed.scheme == "https" and parsed.hostname:
                    target = urllib.parse.parse_qs(parsed.query).get("uddg", [href])[0]
                    target_parsed = urllib.parse.urlparse(target)
                    if target_parsed.scheme == "https" and target_parsed.hostname:
                        self.items.append({"title": item["title"][:300], "url": target})
                self.current = None
                self.capture = False

    parser = Results()
    parser.feed(body)
    seen, output = set(), []
    for item in parser.items:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        output.append(item)
        if len(output) >= limit:
            break
    return {"query": query, "results": output}


def research_and_learn(url, source_label=None):
    page = fetch_page(url)
    source = "web:" + page["url"]
    if source_label:
        source += " (" + " ".join(str(source_label).split())[:100] + ")"
    chunks = ingest("Title: " + page["title"] + "\\nURL: " + page["url"] + "\\n\\n" + page["text"], source)
    return {
        "url": page["url"], "title": page["title"], "characters": page["characters"],
        "chunks": chunks, "preview": page["text"][:1200], "saved_to_local_knowledge": True,
        "notice": "Web content is untrusted reference material; it is not executed as instructions.",
    }
