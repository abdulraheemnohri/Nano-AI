"""Smoke checks for Nano AI HTML and separately served UI assets."""
import re
from fastapi.testclient import TestClient
from nano import app as app_module
from nano import web

def test_home_route_serves_the_application_shell():
    response = TestClient(app_module.app).get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<!doctype html>" in response.text.lower()
    assert "Nano AI" in response.text
    assert '<script src="/assets/nano.js" defer></script>' in response.text
    assert "<script>" not in response.text

def test_static_asset_routes_serve_the_separate_files():
    client = TestClient(app_module.app)
    js = client.get("/assets/nano.js")
    css = client.get("/assets/nano.css")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]
    assert js.text == web.JS and "async function load(p)" in js.text
    assert css.status_code == 200 and "text/css" in css.headers["content-type"]
    assert css.text == web.CSS

def test_each_navigation_target_has_a_matching_page_section():
    html = app_module.HTML
    nav_targets = set(re.findall(r"data-p=\'([^\']+)\'", html))
    page_ids = set(re.findall(r"<section id=\'([^\']+)\' class=\'page", html))
    expected = {"talk", "memory", "learning", "skills", "tools", "knowledge", "research", "automation", "model", "settings", "system"}
    assert expected <= nav_targets
    assert nav_targets <= page_ids, f"Missing page sections: {sorted(nav_targets - page_ids)}"

def test_chat_composer_and_system_diagnostics_controls_are_present():
    required = {"chat", "input", "send", "status", "themeToggle", "systemHealthSummary", "refreshSystemHealth"}
    actual = set(re.findall(r"id=\'([^\']+)\'", app_module.HTML))
    assert required <= actual, f"Missing controls: {sorted(required - actual)}"

def test_api_client_has_token_handling_and_visible_errors():
    assert "sessionStorage.getItem(\'nanoToken\')" in web.JS
    assert "Authorization" in web.JS
    assert "status===401" in web.JS or "status == 401" in web.JS
    assert "throw Error" in web.JS

def test_pagination_failures_are_visible_and_retryable():
    assert "Could not load more conversations:" in web.JS
    assert "Could not load more learning events:" in web.JS
    assert "Could not load more knowledge:" in web.JS
    assert "pagination-error" in web.JS

def test_cancelled_api_token_prompt_can_be_retried():
    assert "else{tokenPrompt=null}" in web.JS

def test_conversation_startup_failure_is_visible_and_retryable():
    assert "Could not load conversations:" in web.JS
    assert "retry.onclick=loadConvs" in web.JS
    assert "startup-error" in web.JS
