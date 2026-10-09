from nano import terminal


def test_terminal_ls_formats_entries_on_separate_lines(tmp_path, monkeypatch):
    (tmp_path / "alpha.txt").write_text("a", encoding="utf-8")
    (tmp_path / "beta.txt").write_text("b", encoding="utf-8")
    monkeypatch.setattr(terminal, "WORKSPACE", tmp_path)

    result = terminal.run_command("ls")

    assert result["status"] == "complete"
    assert result["stdout"].splitlines() == ["f alpha.txt (1 bytes)", "f beta.txt (1 bytes)"]
