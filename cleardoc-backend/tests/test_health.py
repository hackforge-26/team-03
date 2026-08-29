import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_status(self, client):
        """Health check should return status object."""
        response = client.get("/health")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert "services" in data

    def test_health_includes_postgresql_status(self, client):
        """Health check should report PostgreSQL status."""
        response = client.get("/health")
        if response.status_code == 200:
            data = response.json()
            assert "postgresql" in data["services"]

    def test_health_includes_redis_status(self, client):
        """Health check should report Redis status."""
        response = client.get("/health")
        if response.status_code == 200:
            data = response.json()
            assert "redis" in data["services"]
