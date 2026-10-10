from pathlib import Path
from unittest.mock import patch
import zipfile

import pytest

import nano.setup_extras as extras


def test_python_extras_install_does_not_require_source_checkout(monkeypatch):
    with patch.object(extras.subprocess, "run") as run:
        extras._install_python_extras()
    args = run.call_args.args[0]
    assert args[:4] == [extras.sys.executable, "-m", "pip", "install"]
    assert "vosk>=0.3.45" in args
    assert "piper-tts>=1.2.0" in args
    assert "playwright>=1.48" in args
    assert run.call_args.kwargs["check"] is True
    assert "cwd" not in run.call_args.kwargs


def test_piper_voice_download_is_idempotent(tmp_path, monkeypatch):
    model_dir = tmp_path / "piper"
    model = model_dir / "voice.onnx"
    metadata = model_dir / "voice.onnx.json"
    monkeypatch.setattr(extras, "PIPER_DIR", model_dir)
    monkeypatch.setattr(extras, "PIPER_MODEL", model)
    monkeypatch.setattr(extras, "PIPER_CONFIG", metadata)
    calls = []

    def fake_download(url, destination):
        calls.append(url)
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"x" * 2048)

    monkeypatch.setattr(extras, "_download", fake_download)
    assert extras._install_piper_voice() == "downloaded"
    assert model.is_file() and metadata.is_file()
    assert extras._install_piper_voice() == "already-installed"
    assert len(calls) == 2


def test_vosk_zip_extracts_expected_model_safely(tmp_path, monkeypatch):
    model_dir = tmp_path / "vosk-model-small-en-us-0.15"
    archive_path = tmp_path / "model.zip"
    staging = tmp_path / ".vosk-extract"
    monkeypatch.setattr(extras, "VOSK_DIR", model_dir)
    monkeypatch.setattr(extras.config, "MODEL_DIR", tmp_path)

    def fake_download(_url, destination):
        with zipfile.ZipFile(destination, "w") as zipped:
            zipped.writestr("vosk-model-small-en-us-0.15/am/final.mdl", "model")
            zipped.writestr("vosk-model-small-en-us-0.15/conf/model.conf", "config")

    monkeypatch.setattr(extras, "_download", fake_download)
    assert extras._install_vosk_model() == "downloaded"
    assert (model_dir / "am" / "final.mdl").read_text() == "model"
    assert not staging.exists()
    assert not archive_path.exists()


def test_vosk_zip_rejects_path_traversal(tmp_path, monkeypatch):
    model_dir = tmp_path / "vosk-model-small-en-us-0.15"
    monkeypatch.setattr(extras, "VOSK_DIR", model_dir)
    monkeypatch.setattr(extras.config, "MODEL_DIR", tmp_path)

    def fake_download(_url, destination):
        with zipfile.ZipFile(destination, "w") as zipped:
            zipped.writestr("../escaped.txt", "not allowed")
            zipped.writestr("model/am/final.mdl", "model")

    monkeypatch.setattr(extras, "_download", fake_download)
    with pytest.raises(RuntimeError, match="unsafe path"):
        extras._install_vosk_model()
    assert not (tmp_path.parent / "escaped.txt").exists()
