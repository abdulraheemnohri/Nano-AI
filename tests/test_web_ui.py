import re

from nano import web


def test_every_dom_id_referenced_by_the_ui_script_exists_in_the_html():
    html = web.HTML
    referenced = set(re.findall(r"\$\('([^']+)'\)", web.JS))
    defined = set(re.findall(r"id='([^']+)'", html))
    missing = sorted(i for i in referenced if i not in defined)
    assert missing == [], f"UI script references missing element ids: {missing}"


def test_ui_assets_are_separated_and_all_pages_are_present():
    assert '<link rel="stylesheet" href="/assets/nano.css">' in web.HTML
    assert '<script src="/assets/nano.js" defer></script>' in web.HTML
    assert len(web.CSS) > 1000
    for page in ("talk", "memory", "learning", "skills", "tools", "knowledge", "research", "automation", "model", "settings", "system"):
        assert f"id='{page}' class='page" in web.HTML


def test_model_page_wires_auto_setup_cancel_and_progress():
    assert "id='cancelAutoModel'" in web.HTML
    assert "id='autoModelProgress'" in web.HTML
    assert "model_loaded" in web.JS


def test_scheduler_ui_exposes_per_job_run_timeout():
    assert "id='jobTimeout'" in web.HTML
    assert "timeout_seconds:Number($('jobTimeout').value)" in web.JS
    assert "timeout '+(j.timeout_seconds||300)+' sec" in web.JS


def test_model_page_renders_served_and_registry_lists():
    assert "id='modelLists'" in web.HTML
    assert "async function loadModelLists()" in web.JS
    assert "api('/api/models/registry')" in web.JS
    assert "api('/api/health')" in web.JS
    assert "refreshAutoModel(); loadModelLists(); }" in web.JS


def test_sidebar_conversation_paging_wiring():
    assert "async function moreConvs()" in web.JS
    assert "addLoadMoreBtn" in web.JS
    assert "m.id='moreConvs'" in web.JS
    assert "api('/api/conversations?limit=200&offset='+convOffset)" in web.JS


def test_polish_ui_wiring():
    assert "id='themeToggle'" in web.HTML
    assert "b.id='moreLearning'" in web.JS
    assert "b.id='moreKnowledge'" in web.JS
    assert "async function moreLearning()" in web.JS
    assert "async function moreKnowledge()" in web.JS
    assert "id='installUpdateDeps'" in web.HTML
    assert "install_dependencies:$('installUpdateDeps').checked" in web.JS
    assert "api('/api/learning/events?limit=50&offset='+learnOffset)" in web.JS
    assert "api('/api/knowledge?limit=50&offset='+knowledgeOffset)" in web.JS


def test_standalone_web_javascript_parses_with_node():
    import shutil
    import subprocess
    import pytest

    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is not installed; JavaScript syntax check is optional locally")
    result = subprocess.run(
        [node, "--check", "-"],
        input=web.JS,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_web_ui_keeps_core_navigation_and_system_health_controls():
    for expected in ("data-p='talk'", "data-p='settings'", "id='send'", "id='systemHealthSummary'", "id='refreshSystemHealth'"):
        assert expected in web.HTML


def test_chat_loads_paginated_messages_with_earlier_button():
    assert "async function earlierMsgs()" in web.JS
    assert "b.id='earlierMsgs'" in web.JS
    assert "api('/api/conversations/'+id+'/messages?limit='+MSG_PAGE)" in web.JS
    assert "api('/api/conversations/'+cid+'/messages?limit='+MSG_PAGE+'&offset='+msgOffset)" in web.JS
