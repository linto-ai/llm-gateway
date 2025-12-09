"""Test cases for API Key Encryption (TC-501 to TC-502)"""
import pytest
from app.utils import encrypt_api_key, decrypt_api_key
from app.database import Provider

class TestEncryption:
    """Tests for API key encryption"""

    def test_tc501_verify_api_key_never_returned(self, client, db_session):
        """TC-501: Verify API Key Never Returned"""
        # Test CREATE
        create_response = client.post("/api/v1/providers", json={
            "name": "test-encryption",
            "provider_type": "openai",
            "api_base_url": "https://api.openai.com/v1",
            "api_key": "sk-secret-key-12345",
            "security_level": "sensitive"
        })
        assert create_response.status_code == 201
        create_data = create_response.json()
        assert "api_key" not in create_data
        assert create_data["api_key_exists"] is True
        provider_id = create_data["id"]

        # Test GET
        get_response = client.get(f"/api/v1/providers/{provider_id}")
        get_data = get_response.json()
        assert "api_key" not in get_data
        assert get_data["api_key_exists"] is True

        # Test UPDATE
        update_response = client.patch(
            f"/api/v1/providers/{provider_id}",
            json={"api_key": "new-secret-key"}
        )
        update_data = update_response.json()
        assert "api_key" not in update_data
        assert update_data["api_key_exists"] is True

        # Test LIST
        list_response = client.get("/api/v1/providers")
        list_data = list_response.json()
        for provider in list_data["items"]:
            assert "api_key" not in provider
            assert provider["api_key_exists"] is True

    def test_tc502_verify_api_key_encrypted_at_rest(self, client, db_session):
        """TC-502: Verify API Key Encrypted at Rest"""
        plaintext_key = "plaintext-key-12345"

        # Create provider
        response = client.post("/api/v1/providers", json={
            "name": "encryption-test",
            "provider_type": "openai",
            "api_base_url": "https://api.openai.com/v1",
            "api_key": plaintext_key,
            "security_level": "sensitive"
        })
        assert response.status_code == 201
        provider_id = response.json()["id"]

        # Check database directly
        provider = db_session.query(Provider).filter(Provider.id == provider_id).first()
        assert provider is not None

        # Verify encrypted value is different from plaintext
        assert provider.api_key_encrypted != plaintext_key

        # Verify we can decrypt back to plaintext
        decrypted_key = decrypt_api_key(provider.api_key_encrypted)
        assert decrypted_key == plaintext_key
