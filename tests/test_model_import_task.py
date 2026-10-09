import threading
import time

import pytest

from nano import model_manager


def test_start_import_task_rejects_invalid_request():
    with pytest.raises(ValueError):
        model_manager.start_import_task("../bad", "model.litertlm")


def test_start_import_task_reports_running_and_completion(monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def fake_import(repo, filename, model_id):
        started.set()
        release.wait(timeout=2)
        return model_id

    monkeypatch.setattr(model_manager, "import_model", fake_import)
    with model_manager._AUTO_LOCK:
        model_manager._AUTO_STATE.update(status="idle", message="test", model_id=None)
    try:
        state = model_manager.start_import_task("owner/model", "model.litertlm", "custom-model")
        assert state["status"] == "queued"
        assert started.wait(timeout=1)
        active = model_manager.auto_setup_status()
        assert active["status"] == "running"
        assert active["model_id"] == "custom-model"
    finally:
        release.set()
        # Wait briefly for the worker to publish its terminal state.
        for _ in range(100):
            state = model_manager.auto_setup_status()
            if state["status"] == "complete":
                break
            time.sleep(0.01)
        with model_manager._AUTO_LOCK:
            model_manager._AUTO_STATE.update(status="idle", message="test cleanup", model_id=None)
