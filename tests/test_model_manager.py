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
