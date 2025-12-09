"""Test cases for Health Check (TC-601 to TC-602)"""
import pytest

class TestHealthCheck:
    """Tests for GET /healthcheck"""

    def test_tc601_health_check_all_healthy(self, client):
        """TC-601: Health Check - All Healthy"""
        response = client.get("/healthcheck")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "database" in data
        assert "redis" in data
        assert "timestamp" in data

        # Verify timestamp is in ISO 8601 format
        import datetime
        datetime.datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

    def test_tc602_health_check_database_status(self, client):
        """TC-602: Health Check - Database Status"""
        # This test verifies the structure is correct
        # Actual database disconnection testing would require mocking
        response = client.get("/healthcheck")
        assert response.status_code == 200
        data = response.json()

        # Database should be connected in tests
        assert data["database"] in ["connected", "disconnected"]
        assert data["redis"] in ["connected", "disconnected"]
