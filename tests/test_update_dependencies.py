from types import SimpleNamespace
from nano import updates

def test_dependency_update_uses_project_metadata_even_when_requirements_exists(tmp_path, monkeypatch):
    (tmp_path / "requirements.txt").write_text("some-package>=1\n", encoding="utf-8")
    monkeypatch.setattr(updates.config, "ROOT", tmp_path)
    captured = {}
    def fake_run(command, **kwargs):
        captured["command"] = command
        return SimpleNamespace(returncode=0, stderr="", stdout="")
    monkeypatch.setattr(updates.subprocess, "run", fake_run)
    result = updates._install_dependencies()
    assert result["ok"] is True
    assert result["mode"] == "editable"
    assert "-e" in captured["command"]
    assert str(tmp_path) in captured["command"]
    assert "-r" not in captured["command"]
