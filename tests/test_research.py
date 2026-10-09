import pytest

from nano.research import _TextExtractor, _validate_public_url, fetch_page


def test_research_rejects_non_https_and_local_hosts():
    with pytest.raises(ValueError):
        _validate_public_url("http://example.com")
    with pytest.raises(ValueError):
        _validate_public_url("https://localhost/admin")
    with pytest.raises(ValueError):
        _validate_public_url("https://127.0.0.1/")


def test_text_extractor_ignores_script_and_style():
    parser = _TextExtractor()
    parser.feed("<html><title>Example Page</title><body><h1>Hello</h1><script>ignore_me()</script><p>Useful article text.</p></body></html>")
    assert "Example Page" in " ".join(parser.title)
    text = " ".join(parser.parts)
    assert "Useful article text." in text
    assert "ignore_me" not in text


def test_fetch_page_limits_to_readable_page(monkeypatch):
    import nano.research as research
    monkeypatch.setattr(research, "_open", lambda url: ("https://example.com/a", "text/html", "<title>Guide</title><p>" + ("Helpful content " * 20) + "</p>"))
    page = fetch_page("https://example.com/a")
    assert page["title"] == "Guide"
    assert page["url"] == "https://example.com/a"
    assert page["characters"] > 80



def test_text_extractor_keeps_nested_tags_inside_script_blocked():
    parser = _TextExtractor()
    parser.feed(
        "<body><script><div>secret script text</div></script>"
        "<p>Visible useful article text that is long enough.</p></body>"
    )
    text = " ".join(parser.parts)
    assert "secret script text" not in text
    assert "Visible useful article text" in text


def test_dns_validation_rejects_mixed_public_and_private_answers(monkeypatch):
    import socket
    import nano.research as research

    def fake_getaddrinfo(host, port, type):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port)),
        ]

    monkeypatch.setattr(research.socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(ValueError, match="Private"):
        research._validate_public_url("https://rebind.example/article")


def test_research_blocks_nonstandard_https_ports():
    with pytest.raises(ValueError, match="port"):
        _validate_public_url("https://example.com:8443/article")


def test_dns_public_addresses_are_pinned_for_tls_connection():
    import nano.research as research
    connection = research._PinnedHTTPSConnection("example.com", "93.184.216.34")
    assert connection.host == "example.com"
    assert connection._pinned_address == "93.184.216.34"
    assert connection._tls_hostname == "example.com"
    connection.close()


def test_text_extractor_uses_real_newlines_not_literal_backslash_n():
    from nano.research import _TextExtractor

    parser = _TextExtractor()
    parser.feed("<html><body><p>Alpha paragraph.</p><p>Beta paragraph.</p></body></html>")
    text = " ".join(" ".join(parser.parts).split())
    assert text == "Alpha paragraph. Beta paragraph."
    # The bug appended the two-character sequence backslash+n.
    assert "\\n" not in text
    assert "\n" not in text
    # The extractor must emit a real newline character for block tags.
    assert any(part == "\n" for part in parser.parts)
