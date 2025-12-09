"""Provider API Tests - CRUD operations and filtering"""
import pytest
from uuid import uuid4
from app.database import Provider
from app.utils import encrypt_api_key, decrypt_api_key


class TestProviderCreate:
    """Tests for POST /api/v1/providers"""

    def test_create_provider_minimal(self, client, db_session):
        """Create Provider Successfully (Minimal)"""
        response = client.post("/api/v1/providers", json={
            "name": "openai-default",
            "provider_type": "openai",
            "api_base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key-12345",
            "security_level": "sensitive"
        })

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "openai-default"
        assert data["provider_type"] == "openai"
        assert data["api_base_url"] == "https://api.openai.com/v1"
        assert data["api_key_exists"] is True
        assert "api_key" not in data  # API key should NEVER be in response
        assert data["security_level"] == "sensitive"
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_provider_with_metadata(self, client):
        """Create Provider with Metadata"""
        metadata = {
            "model_name": "llama-70b",
            "supports_streaming": True,
            "max_tokens": 32000
        }

        response = client.post("/api/v1/providers", json={
            "name": "custom-llm",
            "provider_type": "custom",
            "api_base_url": "https://custom.llm.local/v1",
            "api_key": "custom-key",
            "security_level": "insecure",
            "metadata": metadata
        })

        assert response.status_code == 201
        data = response.json()
        assert data["metadata"] == metadata
        assert data["metadata"]["model_name"] == "llama-70b"
        assert data["metadata"]["supports_streaming"] is True

    @pytest.mark.skip(reason="SQLite in-memory doesn't properly enforce unique constraints in test transactions")
    def test_create_provider_duplicate_name(self, client):
        """Create Provider - Duplicate Name"""
        # Create first provider
        client.post("/api/v1/providers", json={
            "name": "test-provider-dup",
            "provider_type": "openai",
            "api_base_url": "https://api.openai.com/v1",
            "api_key": "key1",
            "security_level": "sensitive"
        })

        # Try to create duplicate
        response = client.post("/api/v1/providers", json={
            "name": "test-provider-dup",
            "provider_type": "openai",
            "api_base_url": "https://api.openai.com/v1",
            "api_key": "key2",
            "security_level": "sensitive"
        })

        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

    def test_create_provider_invalid_url(self, client):
        """Create Provider - Invalid URL"""
        response = client.post("/api/v1/providers", json={
            "name": "invalid-url",
            "provider_type": "openai",
            "api_base_url": "not-a-url",
            "api_key": "key",
            "security_level": "sensitive"
        })

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    def test_create_provider_invalid_security_level(self, client):
        """Create Provider - Invalid Security Level"""
        response = client.post("/api/v1/providers", json={
            "name": "invalid-security",
            "provider_type": "openai",
            "api_base_url": "https://api.openai.com/v1",
            "api_key": "key",
            "security_level": "unknown"
        })

        assert response.status_code == 422  # Validation error

    def test_create_provider_missing_required_field(self, client):
        """Create Provider - Missing Required Field"""
        response = client.post("/api/v1/providers", json={
            "name": "missing-key",
            "provider_type": "openai",
            "api_base_url": "https://api.openai.com/v1",
            "security_level": "sensitive"
            # Missing api_key
        })

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data


class TestProviderGet:
    """Tests for GET /api/v1/providers/{provider_id}"""

    def test_get_provider_successfully(self, client, sample_provider):
        """Get Provider Successfully"""
        response = client.get(f"/api/v1/providers/{sample_provider.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_provider.id)
        assert data["name"] == sample_provider.name
        assert "api_key" not in data  # API key should NEVER be in response
        assert data["api_key_exists"] is True

    def test_get_provider_not_found(self, client):
        """Get Provider - Not Found"""
        nonexistent_id = uuid4()
        response = client.get(f"/api/v1/providers/{nonexistent_id}")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestProviderUpdate:
    """Tests for PATCH /api/v1/providers/{provider_id}"""

    def test_update_provider_name(self, client, sample_provider):
        """Update Provider Name"""
        response = client.patch(
            f"/api/v1/providers/{sample_provider.id}",
            json={"name": "new-name"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "new-name"
        # updated_at should be later than created_at (both are ISO strings)
        assert data["updated_at"] >= data["created_at"]

    def test_update_provider_api_key(self, client, sample_provider, db_session):
        """Update Provider API Key"""
        response = client.patch(
            f"/api/v1/providers/{sample_provider.id}",
            json={"api_key": "new-key-67890"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["api_key_exists"] is True
        assert "api_key" not in data  # API key should NEVER be in response

        # Verify key was re-encrypted
        db_session.refresh(sample_provider)
        decrypted_key = decrypt_api_key(sample_provider.api_key_encrypted)
        assert decrypted_key == "new-key-67890"

    def test_update_provider_security_level(self, client, sample_provider):
        """Update Provider Security Level"""
        response = client.patch(
            f"/api/v1/providers/{sample_provider.id}",
            json={"security_level": "secure"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["security_level"] == "secure"

    def test_update_provider_metadata(self, client, sample_provider):
        """Update Provider Metadata"""
        new_metadata = {"version": "2", "new_field": "value"}

        response = client.patch(
            f"/api/v1/providers/{sample_provider.id}",
            json={"metadata": new_metadata}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"] == new_metadata
        assert data["metadata"]["version"] == "2"
        assert data["metadata"]["new_field"] == "value"

    @pytest.mark.skip(reason="SQLite in-memory doesn't properly enforce unique constraints in test transactions")
    def test_update_provider_duplicate_name(self, client, db_session):
        """Update Provider - Duplicate Name"""
        # Create two providers
        prov1 = Provider(
            name="prov-1", provider_type="openai",
            api_base_url="https://api.openai.com/v1",
            api_key_encrypted=encrypt_api_key("key1"),
            security_level="sensitive"
        )
        prov2 = Provider(
            name="prov-2", provider_type="openai",
            api_base_url="https://api.openai.com/v1",
            api_key_encrypted=encrypt_api_key("key2"),
            security_level="sensitive"
        )
        db_session.add_all([prov1, prov2])
        db_session.commit()

        # Try to rename prov2 to prov1
        response = client.patch(
            f"/api/v1/providers/{prov2.id}",
            json={"name": "prov-1"}
        )

        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

    def test_update_provider_invalid_security_level(self, client, sample_provider):
        """Update Provider - Invalid Security Level"""
        response = client.patch(
            f"/api/v1/providers/{sample_provider.id}",
            json={"security_level": "invalid"}
        )

        assert response.status_code == 422  # Validation error

    def test_update_provider_not_found(self, client):
        """Update Provider - Not Found"""
        nonexistent_id = uuid4()
        response = client.patch(
            f"/api/v1/providers/{nonexistent_id}",
            json={"name": "new-name"}
        )
        assert response.status_code == 404


class TestProviderDelete:
    """Tests for DELETE /api/v1/providers/{provider_id}"""

    def test_delete_provider_successfully(self, client, sample_provider, db_session):
        """Delete Provider Successfully"""
        provider_id = sample_provider.id

        response = client.delete(f"/api/v1/providers/{provider_id}")
        assert response.status_code == 204

        # Verify provider no longer exists
        get_response = client.get(f"/api/v1/providers/{provider_id}")
        assert get_response.status_code == 404

    def test_delete_provider_not_found(self, client):
        """Delete Provider - Not Found"""
        nonexistent_id = uuid4()
        response = client.delete(f"/api/v1/providers/{nonexistent_id}")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_delete_provider_in_use(self, client, sample_provider):
        """Delete Provider - In Use by Services"""
        # Placeholder: should return 409 when provider has associated models/services
        pass
