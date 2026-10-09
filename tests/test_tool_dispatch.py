import pytest

from nano.db import init_db
from nano.core import _explicit_tool_request, respond
from nano.tools import text_stats


def test_explicit_tool_intent():
    assert _explicit_tool_request("calculate 3 * (4 + 1)") == ("calculator", {"expression": "3 * (4 + 1)"})
    assert _explicit_tool_request("convert 1 km to m") == ("unit_convert", {"value": 1.0, "from_unit": "km", "to_unit": "m"})
    assert _explicit_tool_request("search my memory for solar") == ("memory_search", {"query": "solar"})
    assert _explicit_tool_request("Can you tell me a story?") is None
    assert _explicit_tool_request("what is your name") is None


def test_chat_dispatches_explicit_calculation_without_model(tmp_path, monkeypatch):
    import nano.config as cfg
    db = tmp_path / "dispatch.sqlite3"
    monkeypatch.setattr(cfg, "DB_PATH", db)
    import nano.db as dbm
    monkeypatch.setattr(dbm, "DB_PATH", db)
    import nano.core as core
    monkeypatch.setattr(core, "chat", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("model should not be called")))
    init_db()
    answer = respond(1, "calculate 6 * 7")
    assert answer == "Calculator result: 42"
    from nano.db import rows
    saved = rows("SELECT role,content FROM messages ORDER BY id")
    assert saved[-2]["role"] == "user"
    assert saved[-1]["content"] == "Calculator result: 42"


def test_text_stats_counts_words_and_whitespace():
    result = text_stats("Hello world.\nNano AI!")
    assert result["words"] == 4
    assert result["lines"] == 2
    assert result["characters_without_spaces"] == 18
    assert result["sentences"] == 2
