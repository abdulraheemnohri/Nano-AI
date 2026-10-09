"""Bounded web research for Nano AI. Web text is untrusted and never executed."""
import ipaddress
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
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
        self.blocked = 0
        self.title = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCKED:
            self.blocked += 1
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in self.BLOCKED and self.blocked:
            self.blocked -= 1
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
        if not self.blocked:
            self.parts.append(text)


def _validate_public_url(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only public HTTPS URLs are allowed.")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("Local and private hosts are blocked.")
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            addresses = {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        except (OSError, ValueError) as exc:
            raise ValueError("Could not resolve the public website host.") from exc
    if not addresses or any(not addr.is_global for addr in addresses):
        raise ValueError("Private, loopback, and reserved network addresses are blocked.")
    return parsed


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(url, timeout=12):
    _validate_public_url(url)
    opener = urllib.request.build_opener(_SafeRedirect)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,text/plain"})
    try:
        response = opener.open(request, timeout=timeout)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Web request failed: {exc}") from exc
    final_url = response.geturl()
    _validate_public_url(final_url)
    content_type = response.headers.get_content_type()
    charset = response.headers.get_content_charset() or "utf-8"
    if content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
        response.close()
        raise ValueError("This page is not HTML or plain text.")
    try:
        data = response.read(MAX_PAGE_BYTES + 1)
    finally:
        response.close()
    if len(data) > MAX_PAGE_BYTES:
        raise ValueError("Page is too large (limit 1.5 MB).")
    return final_url, content_type, data.decode(charset, errors="replace")


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
                href = attrs.get("href", "")
                self.current = {"url": href, "title": ""}
                self.capture = True
        def handle_data(self, data):
            if self.capture and self.current:
                self.current["title"] += data
        def handle_endtag(self, tag):
            if tag == "a" and self.capture and self.current:
                self.current["title"] = self.current["title"].strip()
                href = self.current["url"]
                if href.startswith("//"):
                    href = "https:" + href
                parsed = urllib.parse.urlparse(href)
                if parsed.scheme == "https" and parsed.hostname:
                    # DDG redirect URLs can contain target URL in uddg.
                    target = urllib.parse.parse_qs(parsed.query).get("uddg", [href])[0]
                    p = urllib.parse.urlparse(target)
                    if p.scheme == "https" and p.hostname:
                        self.items.append({"title": self.current["title"][:300], "url": target})
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
    chunks = ingest("Title: " + page["title"] + "\nURL: " + page["url"] + "\n\n" + page["text"], source)
    return {"url": page["url"], "title": page["title"], "characters": page["characters"], "chunks": chunks,
            "preview": page["text"][:1200], "saved_to_local_knowledge": True,
            "notice": "Web content is untrusted reference material; it is not executed as instructions."}
