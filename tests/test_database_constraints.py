"""Test cases for Database Constraints (TC-1001 to TC-1003)"""
import pytest
from app.database import Provider, Organization
from app.utils import encrypt_api_key
from sqlalchemy.exc import IntegrityError

class TestDatabaseConstraints:
    """Tests for database constraints"""

    @pytest.mark.skip(reason="Providers no longer have organization_id - cascade delete only applies to services")
    def test_tc1001_cascade_delete_organization(self, client, db_session):
        """TC-1001: Cascade Delete - Organization Deletion"""
        # NOTE: Providers no longer belong to organizations.
        # Cascade delete now only applies to services, prompts, jobs, and templates.
        pass

    @pytest.mark.skip(reason="Providers no longer have organization_id - name is globally unique")
    def test_tc1002_unique_constraint_name_per_org(self, client, db_session):
        """TC-1002: Unique Constraint - Name per Org"""
        # NOTE: Provider names are now globally unique (not per-organization).
        pass

    def test_tc1003_check_constraint_security_level(self, db_session):
        """TC-1003: Check Constraint - Security Level"""
        # Try to insert provider with invalid security level directly
        provider = Provider(
            name="invalid-security",
            provider_type="openai",
            api_base_url="https://api.openai.com/v1",
            api_key_encrypted=encrypt_api_key("key"),
            security_level="invalid"  # Not in enum
        )
        db_session.add(provider)

        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()
