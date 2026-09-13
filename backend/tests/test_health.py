from fastapi.testclient import TestClient

from app.main import app


def test_config_surfaces_active_provider(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    client = TestClient(app)
    response = client.get("/config")
    assert response.status_code == 200
    assert response.json()["provider"] == "ollama"


def test_health_reports_database_state(monkeypatch):
    monkeypatch.setattr("app.main.database_status", lambda: ("down", "OperationalError"))
    response = TestClient(app).get("/health")
    assert response.status_code == 503
    assert response.json()["dependencies"]["database"]["status"] == "down"
    assert response.headers["X-Request-ID"]
