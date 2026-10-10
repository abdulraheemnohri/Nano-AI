import threading

from nano import model_manager


def test_auto_setup_does_not_start_duplicate_worker(monkeypatch):
    started = threading.Event()
    release = threading.Event()
    calls = []

    def worker():
        calls.append(True)
        started.set()
        release.wait(timeout=2)

    monkeypatch.setattr(model_manager, "_auto_setup_worker", worker)
    with model_manager._AUTO_LOCK:
        model_manager._AUTO_STATE.update(status="idle", message="test", model_id=None)

    try:
        model_manager.start_auto_setup()
        assert started.wait(timeout=1)
        second = model_manager.start_auto_setup()
        assert second["status"] == "queued"
        assert len(calls) == 1
    finally:
        release.set()
        with model_manager._AUTO_LOCK:
            model_manager._AUTO_STATE.update(status="idle", message="test cleanup", model_id=None)


def test_model_import_state_is_persisted(monkeypatch, tmp_path):
    state_file = tmp_path / "model-import-state.json"
    monkeypatch.setattr(model_manager, "_STATE_FILE", state_file)
    model_manager._set_task(status="running", phase="downloading", progress=37, message="test")
    import json
    saved = json.loads(state_file.read_text(encoding="utf-8"))
    assert saved["status"] == "running"
    assert saved["progress"] == 37

def test_registry_model_match_requires_a_complete_identifier():
    assert model_manager._registry_has_model([{"raw": "qwen3-1.7b READY"}], "qwen3-1.7b")
    assert not model_manager._registry_has_model([{"raw": "qwen3-1.7b-custom READY"}], "qwen3-1.7b")
    assert not model_manager._registry_has_model([{"raw": "my-qwen3-1.7b READY"}], "qwen3-1.7b")
    assert model_manager._registry_has_model([{"id": "Qwen3-1.7B"}], "qwen3-1.7b")
