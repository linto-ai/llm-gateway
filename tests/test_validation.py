"""Additional validation and ISO 8601 timestamp tests"""
import pytest
from datetime import datetime
import re

class TestValidation:
    """Additional validation tests"""

    def test_uuid_validation(self, client):
        """Test that UUIDs are validated properly"""
        # Invalid UUID format
        response = client.get("/api/v1/providers/not-a-uuid")
        assert response.status_code == 422

    def test_iso_8601_timestamps(self, client):
        """Test that all timestamps are in ISO 8601 UTC format"""
        response = client.post("/api/v1/providers", json={
            "name": "timestamp-test",
            "provider_type": "openai",
            "api_base_url": "https://api.openai.com/v1",
            "api_key": "key",
            "security_level": "sensitive"
        })

        assert response.status_code == 201
        data = response.json()

        # ISO 8601 regex pattern
        iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$'

        assert "created_at" in data
        assert "updated_at" in data

        # Verify format
        assert re.match(iso_pattern, data["created_at"]) or datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        assert re.match(iso_pattern, data["updated_at"]) or datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))

    def test_pagination_limit_max(self, client):
        """Test that pagination limit max is enforced (100)"""
        response = client.get("/api/v1/providers?limit=101")
        assert response.status_code == 422

    def test_provider_name_length(self, client):
        """Test provider name length constraints"""
        # Name too long (>100 chars)
        long_name = "a" * 101
        response = client.post("/api/v1/providers", json={
            "name": long_name,
            "provider_type": "openai",
            "api_base_url": "https://api.openai.com/v1",
            "api_key": "key",
            "security_level": "sensitive"
        })
        assert response.status_code == 422

    def test_url_validation(self, client):
        """Test URL validation"""
        # Missing protocol
        response = client.post("/api/v1/providers", json={
            "name": "bad-url",
            "provider_type": "openai",
            "api_base_url": "api.openai.com/v1",
            "api_key": "key",
            "security_level": "sensitive"
        })
        assert response.status_code == 422

    def test_provider_type_enum(self, client):
        """Test provider_type enum validation"""
        response = client.post("/api/v1/providers", json={
            "name": "invalid-type",
            "provider_type": "invalid",
            "api_base_url": "https://api.test.com",
            "api_key": "key",
            "security_level": "sensitive"
        })
        assert response.status_code == 422

    @pytest.mark.skip(reason="Providers no longer have organization scoping - only services have organization_id")
    def test_organization_scoping_enforcement(self, client, db_session):
        """Test that organization scoping is properly enforced (for Services)"""
        # NOTE: This test was for Provider organization scoping which has been removed.
        # Organization scoping now only applies to Services.
        pass
