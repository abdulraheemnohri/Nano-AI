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
