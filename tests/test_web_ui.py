import re

from nano import web


def test_every_dom_id_referenced_by_the_ui_script_exists_in_the_html():
    html = web.HTML
    referenced = set(re.findall(r"\$\('([^']+)'\)", html))
    defined = set(re.findall(r"id='([^']+)'", html))
    missing = sorted(i for i in referenced if i not in defined)
    assert missing == [], f"UI script references missing element ids: {missing}"


def test_model_page_wires_auto_setup_cancel_and_progress():
    html = web.HTML
    assert "id='cancelAutoModel'" in html
    assert "id='autoModelProgress'" in html
    assert "model_loaded" in html

def test_scheduler_ui_exposes_per_job_run_timeout():
    html = web.HTML
    assert "id='jobTimeout'" in html
    assert "timeout_seconds:Number($('jobTimeout').value)" in html
    assert "timeout '+(j.timeout_seconds||300)+' sec" in html


def test_model_page_renders_served_and_registry_lists():
    html = web.HTML
    assert "id='modelLists'" in html
    assert "async function loadModelLists()" in html
    assert "api('/api/models/registry')" in html
    assert "api('/api/health')" in html
    assert "refreshAutoModel(); loadModelLists(); }" in html

def test_sidebar_conversation_paging_wiring():
    html = web.HTML
    assert "async function moreConvs()" in html
    assert "addLoadMoreBtn" in html
    assert "m.id='moreConvs'" in html
    assert "api('/api/conversations?limit=200&offset='+convOffset)" in html


def test_polish_ui_wiring():
    html = web.HTML
    assert "id='themeToggle'" in html
    assert "b.id='moreLearning'" in html
    assert "b.id='moreKnowledge'" in html
    assert "async function moreLearning()" in html
    assert "async function moreKnowledge()" in html
    assert "id='installUpdateDeps'" in html
    assert "install_dependencies:$('installUpdateDeps').checked" in html
    assert "api('/api/learning/events?limit=50&offset='+learnOffset)" in html
    assert "api('/api/knowledge?limit=50&offset='+knowledgeOffset)" in html
