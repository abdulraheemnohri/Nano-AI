import types

import pytest

from nano import config, model_manager


def _low_space(monkeypatch, tmp_path, free):
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path)
    usage = types.SimpleNamespace(free=free, total=free + 100, used=100)
    monkeypatch.setattr(model_manager.shutil, "disk_usage", lambda path: usage)


def test_ensure_disk_space_blocks_low_free_space(tmp_path, monkeypatch):
    _low_space(monkeypatch, tmp_path, free=500 * 1024 * 1024)
    with pytest.raises(ValueError, match="free disk space"):
        model_manager.ensure_disk_space()


def test_ensure_disk_space_passes_with_enough_space(tmp_path, monkeypatch):
    _low_space(monkeypatch, tmp_path, free=3 * 1024 * 1024 * 1024)
    result = model_manager.ensure_disk_space()
    assert result["free_bytes"] >= result["required_bytes"]


def test_import_task_refused_without_disk_space(tmp_path, monkeypatch):
    _low_space(monkeypatch, tmp_path, free=100)
    with pytest.raises(ValueError, match="free disk space"):
        model_manager.start_import_task("litert-community/Qwen3-4B-Thinking-2507", "Qwen3_4b_thinking_dynamic_wi4b32_afp32.litertlm", "qwen3-4b-thinking-2507")
