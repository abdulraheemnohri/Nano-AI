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
