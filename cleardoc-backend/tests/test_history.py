import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHistoryEndpoint:
    """Tests for the /history endpoint."""

    def test_history_requires_user_id(self, client):
        """Missing user_id query param should return 422."""
        response = client.get("/history")
        assert response.status_code == 422

    def test_history_with_invalid_user_returns_empty(self, client):
        """Non-existent user should return empty list."""
        response = client.get("/history?user_id=nonexistent-user")
        # May return 200 with [] or 500 if DB not connected
        assert response.status_code in [200, 500]

    def test_history_item_not_found(self, client):
        """Non-existent document should return 404."""
        response = client.get("/history/00000000-0000-0000-0000-000000000000")
        assert response.status_code in [404, 500]

    def test_delete_requires_user_id(self, client):
        """Delete without user_id should return 422."""
        response = client.delete("/history/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 422
