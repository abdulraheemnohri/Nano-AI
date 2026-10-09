import pytest

from nano.db import init_db
from nano.tools import calculator, text_stats, unit_convert, list_tools, run_tool


def test_calculator_safe_arithmetic():
    assert calculator("(2 + 3) * 4")["result"] == 20
    with pytest.raises(ValueError):
        calculator("__import__('os').system('echo unsafe')")
    with pytest.raises(ValueError):
        calculator("2 ** 1000")


def test_unit_conversion():
    assert unit_convert(1, "km", "m")["result"] == 1000
    assert unit_convert(0, "c", "f")["result"] == pytest.approx(32)
    with pytest.raises(ValueError):
        unit_convert(1, "kg", "m")


def test_text_stats():
    result = text_stats("Hello world.\nNano AI!")
    assert result["words"] == 4
    assert result["lines"] == 2
    assert result["sentences"] == 2


def test_tool_registry_and_disabled_tool(tmp_path, monkeypatch):
    import nano.config as cfg
    db = tmp_path / "tools.sqlite3"
    monkeypatch.setattr(cfg, "DB_PATH", db)
    import nano.db as dbm
    monkeypatch.setattr(dbm, "DB_PATH", db)
    init_db()
    assert {item["name"] for item in list_tools()} >= {"calculator", "datetime_now", "unit_convert", "text_stats", "memory_search", "knowledge_search"}
    assert run_tool("calculator", {"expression": "6*7"})["result"]["result"] == 42
    from nano.tools import set_enabled
    set_enabled("calculator", False)
    with pytest.raises(PermissionError):
        run_tool("calculator", {"expression": "1+1"})
    set_enabled("calculator", True)
