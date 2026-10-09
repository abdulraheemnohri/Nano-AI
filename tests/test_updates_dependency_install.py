import types

import nano.updates as updates


def _fake_run_factory(calls, returncode=0, stderr=""):
    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return types.SimpleNamespace(returncode=returncode, stdout="", stderr=stderr)
    return fake_run


def test_install_dependencies_uses_requirements_file(tmp_path, monkeypatch):
    (tmp_path / "requirements.txt").write_text("fastapi\n")
    monkeypatch.setattr(updates.config, "ROOT", tmp_path)
    calls = []
    monkeypatch.setattr(updates.subprocess, "run", _fake_run_factory(calls, returncode=0))
    result = updates._install_dependencies()
    assert result["ok"] is True
    assert result["mode"] == "requirements"
    assert any(part == "-r" for part in calls[0])


def test_install_dependencies_falls_back_to_editable(tmp_path, monkeypatch):
    monkeypatch.setattr(updates.config, "ROOT", tmp_path)
    calls = []
    monkeypatch.setattr(updates.subprocess, "run", _fake_run_factory(calls, returncode=0))
    result = updates._install_dependencies()
    assert result["ok"] is True
    assert result["mode"] == "editable"
    assert any(part == "-e" for part in calls[0])


def test_install_dependencies_reports_pip_failure(tmp_path, monkeypatch):
    (tmp_path / "requirements.txt").write_text("fastapi\n")
    monkeypatch.setattr(updates.config, "ROOT", tmp_path)
    calls = []
    monkeypatch.setattr(updates.subprocess, "run", _fake_run_factory(calls, returncode=1, stderr="boom"))
    result = updates._install_dependencies()
    assert result["ok"] is False
    assert "boom" in result["error"]
