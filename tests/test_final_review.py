from nano import terminal


def test_terminal_ls_formats_entries_on_separate_lines(tmp_path, monkeypatch):
    (tmp_path / "alpha.txt").write_text("a", encoding="utf-8")
    (tmp_path / "beta.txt").write_text("b", encoding="utf-8")
    monkeypatch.setattr(terminal, "WORKSPACE", tmp_path)

    result = terminal.run_command("ls")

    assert result["status"] == "complete"
    assert result["stdout"].splitlines() == ["f alpha.txt (1 bytes)", "f beta.txt (1 bytes)"]

def test_update_recovery_manifest_is_valid_json_with_real_trailing_newline(tmp_path, monkeypatch):
    import json
    import nano.config as config
    import nano.updates as updates

    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    manifest = {
        "repository": "abdulraheemnohri/Nano-AI",
        "previous_sha": "a" * 40,
        "current_sha": "b" * 40,
        "database_snapshot": None,
        "dependency_files_changed": [],
    }

    updates._write_recovery_manifest(manifest)
    _, path = updates._recovery_paths()
    raw = path.read_text(encoding="utf-8")

    assert raw.endswith("\\n")
    assert not raw.endswith("\\\\n")
    assert json.loads(raw) == manifest

