from fastapi.testclient import TestClient

from nano import app as app_module


def test_ready_endpoint_requires_served_model(monkeypatch):
    def fake_status():
        return {"runtime":"litert-lm","configured_url":"http://127.0.0.1:9379","model":"qwen3-4b-thinking-2507",
                "reachable":True,"binary":True,"models":["other-model"],"registry":[],"endpoint_error":None}
    monkeypatch.setattr(app_module, "status", fake_status)
    client = TestClient(app_module.app)

    response = client.get("/api/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["ready"] is False
    assert body["model_reachable"] is True
    assert body["model_ready"] is False
    assert "nano-ai download-model" in body["model_readiness"]["detail"]


def test_ready_endpoint_ok_when_model_served(monkeypatch):
    def fake_status():
        return {"runtime":"litert-lm","configured_url":"http://127.0.0.1:9379","model":"qwen3-4b-thinking-2507",
                "reachable":True,"binary":True,"models":["qwen3-4b-thinking-2507"],"registry":[],"endpoint_error":None}
    monkeypatch.setattr(app_module, "status", fake_status)
    client = TestClient(app_module.app)

    response = client.get("/api/ready")
    body = response.json()

    assert response.status_code == 200
    assert body["ready"] is True
    assert body["model_ready"] is True


def test_health_endpoint_reports_model_readiness(monkeypatch):
    def fake_status():
        return {"runtime":"litert-lm","configured_url":"http://127.0.0.1:9379","model":"qwen3-4b-thinking-2507",
                "reachable":False,"binary":True,"models":[],"registry":[],"endpoint_error":"Connection refused"}
    monkeypatch.setattr(app_module, "status", fake_status)
    client = TestClient(app_module.app)

    response = client.get("/api/health")
    body = response.json()

    assert body["ok"] is True
    assert body["model_ready"] is False
    assert "nano-ai litert-lm" in body["model_readiness"]["detail"]
    assert "Connection refused" in body["model_readiness"]["detail"]
