"""End-to-end smoke checks for the embedded Nano AI web application.

These tests exercise the actual FastAPI route as well as the HTML contract the
browser depends on. They intentionally avoid starting LiteRT-LM or optional
voice/browser services.
"""
import re

from fastapi.testclient import TestClient

from nano import app as app_module


def test_home_route_serves_the_embedded_application():
    response = TestClient(app_module.app).get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<!doctype html>" in response.text.lower()
    assert "Nano AI" in response.text
    assert "<script>" in response.text


def test_each_navigation_target_has_a_matching_page_section():
    html = app_module.HTML
    nav_targets = set(re.findall(r"data-p='([^']+)'", html))
    page_ids = set(re.findall(r"<section id='([^']+)' class='page", html))

    assert {"talk", "memory", "learning", "skills", "tools", "knowledge",
            "research", "automation", "model", "settings", "system"} <= nav_targets
    assert nav_targets <= page_ids, (
        "Navigation buttons point to pages that do not exist: "
        f"{sorted(nav_targets - page_ids)}"
    )


def test_chat_composer_and_system_diagnostics_controls_are_present():
    html = app_module.HTML
    required_ids = {
        "chat", "input", "send", "status", "themeToggle",
        "systemHealthSummary", "refreshSystemHealth",
    }
    actual_ids = set(re.findall(r"id='([^']+)'", html))

    assert required_ids <= actual_ids, (
        f"Missing web UI controls: {sorted(required_ids - actual_ids)}"
    )


def test_embedded_ui_has_auth_aware_api_client_and_visible_errors():
    html = app_module.HTML

    # The API client must attach a browser-session token when configured and
    # provide a way to recover from a 401 instead of silently failing requests.
    assert "sessionStorage.getItem('nanoToken')" in html
    assert "Authorization" in html
    assert "status===401" in html or "status == 401" in html
    assert "throw Error" in html


def test_pagination_failures_are_visible_and_retryable():
    from nano import web

    html = web.HTML
    assert "Could not load more conversations:" in html
    assert "Could not load more learning events:" in html
    assert "Could not load more knowledge:" in html
    assert "pagination-error" in html

def test_cancelled_api_token_prompt_can_be_retried():
    from nano import web

    # Cancelling prompt() must not leave a resolved empty token cached forever.
    assert "else{tokenPrompt=null}" in web.HTML

def test_conversation_startup_failure_is_visible_and_retryable():
    from nano import web

    assert "Could not load conversations:" in web.HTML
    assert "retry.onclick=loadConvs" in web.HTML
    assert "startup-error" in web.HTML
