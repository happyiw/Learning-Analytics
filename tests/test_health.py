from fastapi.testclient import TestClient

from backend.main import app


def test_liveness_and_root():
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert response.headers["X-Request-ID"]


def test_metrics_endpoint():
    with TestClient(app) as client:
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "learning_analytics_http_requests_total" in response.text
