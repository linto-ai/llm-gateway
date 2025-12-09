"""Tests for the failover chain feature.

This module tests:
1. Cycle detection in failover chains
2. Failover chain retrieval
3. API endpoints for failover chain management
4. Failoverable exception types
"""
import os
import pytest
import pytest_asyncio
from uuid import uuid4


# Helper to detect SQLite environment (tests use SQLite by default)
def is_sqlite_db():
    """Check if the test database is SQLite (JSONB not supported)."""
    db_url = os.environ.get("DATABASE_URL", "sqlite")
    return "sqlite" in db_url.lower()


# Skip marker for tests requiring PostgreSQL (JSONB support)
requires_postgresql = pytest.mark.skipif(
    is_sqlite_db(),
    reason="Requires PostgreSQL (JSONB not supported in SQLite)"
)

from app.models.service_flavor import ServiceFlavor
from app.models.service import Service
from app.models.model import Model
from app.services.failover_service import FailoverService, failover_service
from app.core.exceptions import (
    FailoverableError,
    TimeoutFailoverError,
    RateLimitFailoverError,
    ModelFailoverError,
    ContentFilterFailoverError,
)


# =============================================================================
# Exception Tests
# =============================================================================

class TestFailoverableExceptions:
    """Tests for failoverable exception types."""

    def test_failoverable_error_base(self):
        """Test FailoverableError base class."""
        error = FailoverableError("Test error", "timeout", ValueError("original"))
        assert str(error) == "Test error"
        assert error.failover_reason == "timeout"
        assert isinstance(error.original_error, ValueError)

    def test_timeout_failover_error(self):
        """Test TimeoutFailoverError."""
        error = TimeoutFailoverError("API timeout after 3 retries")
        assert error.failover_reason == "timeout"
        assert "timeout" in str(error).lower()

    def test_rate_limit_failover_error(self):
        """Test RateLimitFailoverError."""
        error = RateLimitFailoverError("Rate limit exceeded")
        assert error.failover_reason == "rate_limit"

    def test_model_failover_error(self):
        """Test ModelFailoverError."""
        error = ModelFailoverError("Model unavailable (HTTP 503)")
        assert error.failover_reason == "model_error"

    def test_content_filter_failover_error(self):
        """Test ContentFilterFailoverError."""
        error = ContentFilterFailoverError("Content blocked by policy")
        assert error.failover_reason == "content_filter"


# =============================================================================
# Failover Service Unit Tests
# =============================================================================

@requires_postgresql
class TestFailoverServiceValidation:
    """Tests for failover chain validation (cycle detection)."""

    @pytest.mark.asyncio
    async def test_validate_self_reference(self, async_db_session, async_sample_model):
        """Direct self-reference (A -> A) should be rejected."""
        # Create a service and flavor
        service = Service(
            name="Test Service",
            route="test-service",
            service_type="summary",
            is_active=True
        )
        async_db_session.add(service)
        await async_db_session.commit()

        flavor = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="flavor-a",
            temperature=0.7,
            top_p=0.9
        )
        async_db_session.add(flavor)
        await async_db_session.commit()

        # Validate self-reference
        is_valid, error, depth, preview = await failover_service.validate_failover_chain(
            async_db_session, flavor.id, flavor.id
        )

        assert is_valid is False
        assert "self" in error.lower()
        assert depth == 0

    @pytest.mark.asyncio
    async def test_validate_indirect_cycle(self, async_db_session, async_sample_model):
        """Indirect cycle (A -> B -> A) should be detected."""
        service = Service(
            name="Test Service Cycle",
            route="test-service-cycle",
            service_type="summary",
            is_active=True
        )
        async_db_session.add(service)
        await async_db_session.commit()

        flavor_a = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="flavor-a",
            temperature=0.7,
            top_p=0.9
        )
        async_db_session.add(flavor_a)
        await async_db_session.commit()

        flavor_b = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="flavor-b",
            temperature=0.5,
            top_p=0.8,
            failover_flavor_id=flavor_a.id  # B -> A
        )
        async_db_session.add(flavor_b)
        await async_db_session.commit()

        # Now try to set A -> B (would create A -> B -> A cycle)
        is_valid, error, depth, preview = await failover_service.validate_failover_chain(
            async_db_session, flavor_a.id, flavor_b.id
        )

        assert is_valid is False
        assert "cycle" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_deep_cycle(self, async_db_session, async_sample_model):
        """Deep cycle (A -> B -> C -> A) should be detected."""
        service = Service(
            name="Test Deep Cycle",
            route="test-deep-cycle",
            service_type="summary",
            is_active=True
        )
        async_db_session.add(service)
        await async_db_session.commit()

        flavor_a = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="flavor-a",
            temperature=0.7,
            top_p=0.9
        )
        async_db_session.add(flavor_a)
        await async_db_session.commit()

        flavor_b = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="flavor-b",
            temperature=0.5,
            top_p=0.8
        )
        async_db_session.add(flavor_b)
        await async_db_session.commit()

        flavor_c = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="flavor-c",
            temperature=0.3,
            top_p=0.7,
            failover_flavor_id=flavor_a.id  # C -> A
        )
        async_db_session.add(flavor_c)
        await async_db_session.commit()

        # Set B -> C
        flavor_b.failover_flavor_id = flavor_c.id
        await async_db_session.commit()

        # Now try to set A -> B (would create A -> B -> C -> A cycle)
        is_valid, error, depth, preview = await failover_service.validate_failover_chain(
            async_db_session, flavor_a.id, flavor_b.id
        )

        assert is_valid is False
        assert "cycle" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_valid_chain(self, async_db_session, async_sample_model):
        """Valid chain (A -> B -> C -> null) should be accepted."""
        service = Service(
            name="Test Valid Chain",
            route="test-valid-chain",
            service_type="summary",
            is_active=True
        )
        async_db_session.add(service)
        await async_db_session.commit()

        flavor_a = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="flavor-a",
            temperature=0.7,
            top_p=0.9
        )
        flavor_b = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="flavor-b",
            temperature=0.5,
            top_p=0.8
        )
        flavor_c = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="flavor-c",
            temperature=0.3,
            top_p=0.7
        )
        async_db_session.add_all([flavor_a, flavor_b, flavor_c])
        await async_db_session.commit()

        # Set up chain: B -> C
        flavor_b.failover_flavor_id = flavor_c.id
        await async_db_session.commit()

        # Validate A -> B (valid chain: A -> B -> C -> null)
        is_valid, error, depth, preview = await failover_service.validate_failover_chain(
            async_db_session, flavor_a.id, flavor_b.id
        )

        assert is_valid is True
        assert error is None
        assert depth == 3  # A, B, C
        assert len(preview) == 3


@requires_postgresql
class TestFailoverServiceChainRetrieval:
    """Tests for failover chain retrieval."""

    @pytest.mark.asyncio
    async def test_get_single_flavor_chain(self, async_db_session, async_sample_model):
        """Chain with single flavor (no failover configured)."""
        service = Service(
            name="Single Flavor Service",
            route="single-flavor",
            service_type="summary",
            is_active=True
        )
        async_db_session.add(service)
        await async_db_session.commit()

        flavor = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="solo-flavor",
            temperature=0.7,
            top_p=0.9
        )
        async_db_session.add(flavor)
        await async_db_session.commit()

        chain, has_cycle = await failover_service.get_failover_chain(async_db_session, flavor.id)

        assert len(chain) == 1
        assert chain[0]["name"] == "solo-flavor"
        assert chain[0]["depth"] == 0
        assert has_cycle is False

    @pytest.mark.asyncio
    async def test_get_multi_flavor_chain(self, async_db_session, async_sample_model):
        """Chain with multiple flavors."""
        service = Service(
            name="Multi Flavor Service",
            route="multi-flavor",
            service_type="summary",
            is_active=True
        )
        async_db_session.add(service)
        await async_db_session.commit()

        flavor_a = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="primary",
            temperature=0.7,
            top_p=0.9
        )
        flavor_b = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="secondary",
            temperature=0.5,
            top_p=0.8
        )
        flavor_c = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="tertiary",
            temperature=0.3,
            top_p=0.7
        )
        async_db_session.add_all([flavor_a, flavor_b, flavor_c])
        await async_db_session.commit()

        # Set up chain: A -> B -> C
        flavor_a.failover_flavor_id = flavor_b.id
        flavor_b.failover_flavor_id = flavor_c.id
        await async_db_session.commit()

        chain, has_cycle = await failover_service.get_failover_chain(async_db_session, flavor_a.id)

        assert len(chain) == 3
        assert chain[0]["name"] == "primary"
        assert chain[0]["depth"] == 0
        assert chain[1]["name"] == "secondary"
        assert chain[1]["depth"] == 1
        assert chain[2]["name"] == "tertiary"
        assert chain[2]["depth"] == 2
        assert has_cycle is False

    @pytest.mark.asyncio
    async def test_get_flavor_by_id(self, async_db_session, async_sample_model):
        """Test get_flavor_by_id helper."""
        service = Service(
            name="Test Get Flavor",
            route="test-get-flavor",
            service_type="summary",
            is_active=True
        )
        async_db_session.add(service)
        await async_db_session.commit()

        flavor = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="test-flavor",
            temperature=0.7,
            top_p=0.9
        )
        async_db_session.add(flavor)
        await async_db_session.commit()

        result = await failover_service.get_flavor_by_id(async_db_session, flavor.id)

        assert result is not None
        assert result.name == "test-flavor"
        assert result.model is not None  # Relationship loaded
        assert result.service is not None  # Relationship loaded

    @pytest.mark.asyncio
    async def test_get_nonexistent_flavor(self, async_db_session):
        """Test get_flavor_by_id with non-existent ID."""
        result = await failover_service.get_flavor_by_id(async_db_session, uuid4())
        assert result is None


# =============================================================================
# Schema Validation Tests
# =============================================================================

class TestFailoverSchemas:
    """Tests for failover-related Pydantic schemas."""

    def test_service_flavor_base_failover_fields(self):
        """Test ServiceFlavorBase includes failover fields."""
        from app.schemas.service import ServiceFlavorBase

        fields = set(ServiceFlavorBase.model_fields.keys())
        assert "failover_flavor_id" in fields
        assert "failover_enabled" in fields
        assert "failover_on_timeout" in fields
        assert "failover_on_rate_limit" in fields
        assert "failover_on_model_error" in fields
        assert "failover_on_content_filter" in fields
        assert "max_failover_depth" in fields

    def test_service_flavor_update_failover_fields(self):
        """Test ServiceFlavorUpdate includes failover fields."""
        from app.schemas.service import ServiceFlavorUpdate

        fields = set(ServiceFlavorUpdate.model_fields.keys())
        assert "failover_flavor_id" in fields
        assert "failover_enabled" in fields
        assert "failover_on_timeout" in fields
        assert "failover_on_rate_limit" in fields
        assert "failover_on_model_error" in fields
        assert "failover_on_content_filter" in fields
        assert "max_failover_depth" in fields

    def test_service_flavor_response_failover_fields(self):
        """Test ServiceFlavorResponse includes failover fields."""
        from app.schemas.service import ServiceFlavorResponse

        fields = set(ServiceFlavorResponse.model_fields.keys())
        assert "failover_flavor_id" in fields
        assert "failover_flavor_name" in fields
        assert "failover_service_name" in fields
        assert "failover_enabled" in fields
        assert "failover_on_timeout" in fields
        assert "failover_on_rate_limit" in fields
        assert "failover_on_model_error" in fields
        assert "failover_on_content_filter" in fields
        assert "max_failover_depth" in fields

    def test_failover_chain_response_schema(self):
        """Test FailoverChainResponse schema."""
        from app.schemas.service import FailoverChainResponse, FailoverChainItem

        # Test valid data
        chain = FailoverChainResponse(
            chain=[
                FailoverChainItem(
                    id="uuid-1",
                    name="primary",
                    service_id="service-uuid",
                    service_name="Test Service",
                    model_name="gpt-4",
                    is_active=True,
                    depth=0
                )
            ],
            max_depth=3,
            has_cycle=False
        )
        assert len(chain.chain) == 1
        assert chain.max_depth == 3
        assert chain.has_cycle is False

    def test_validate_failover_request_schema(self):
        """Test ValidateFailoverRequest schema."""
        from app.schemas.service import ValidateFailoverRequest
        from uuid import uuid4

        request = ValidateFailoverRequest(failover_flavor_id=uuid4())
        assert request.failover_flavor_id is not None

    def test_validate_failover_response_schema(self):
        """Test ValidateFailoverResponse schema."""
        from app.schemas.service import ValidateFailoverResponse

        # Valid response
        response = ValidateFailoverResponse(
            valid=True,
            error=None,
            chain_depth=3,
            chain_preview=["primary", "secondary", "tertiary"]
        )
        assert response.valid is True
        assert len(response.chain_preview) == 3

        # Invalid response
        response = ValidateFailoverResponse(
            valid=False,
            error="Cycle detected",
            chain_depth=2,
            chain_preview=["primary", "secondary"]
        )
        assert response.valid is False
        assert response.error == "Cycle detected"

    def test_max_failover_depth_validation(self):
        """Test max_failover_depth range validation (1-10)."""
        from app.schemas.service import ServiceFlavorBase
        from pydantic import ValidationError
        from uuid import uuid4

        # Valid values
        for depth in [1, 3, 5, 10]:
            schema = ServiceFlavorBase(
                name="test",
                model_id=uuid4(),
                temperature=0.7,
                max_failover_depth=depth
            )
            assert schema.max_failover_depth == depth

        # Invalid values
        for depth in [0, -1, 11, 100]:
            with pytest.raises(ValidationError):
                ServiceFlavorBase(
                    name="test",
                    model_id=uuid4(),
                    temperature=0.7,
                    max_failover_depth=depth
                )


# =============================================================================
# Model Tests
# =============================================================================

class TestFailoverModelConstraints:
    """Tests for database model constraints."""

    def test_service_flavor_has_failover_columns(self):
        """Test ServiceFlavor model has failover columns."""
        columns = {c.name for c in ServiceFlavor.__table__.columns}
        assert "failover_flavor_id" in columns
        assert "failover_enabled" in columns
        assert "failover_on_timeout" in columns
        assert "failover_on_rate_limit" in columns
        assert "failover_on_model_error" in columns
        assert "failover_on_content_filter" in columns
        assert "max_failover_depth" in columns

    def test_service_flavor_failover_relationship(self):
        """Test ServiceFlavor has failover_flavor relationship."""
        from sqlalchemy.orm import RelationshipProperty

        mapper = ServiceFlavor.__mapper__
        assert "failover_flavor" in mapper.relationships
        rel = mapper.relationships["failover_flavor"]
        assert isinstance(rel, RelationshipProperty)

    def test_check_constraints_defined(self):
        """Test check constraints are defined in model."""
        constraints = {c.name for c in ServiceFlavor.__table__.constraints if c.name}
        assert "check_no_self_failover" in constraints
        assert "check_max_failover_depth" in constraints


# =============================================================================
# API Endpoint Tests
# =============================================================================

@requires_postgresql
class TestFailoverAPIEndpoints:
    """Tests for failover chain API endpoints."""

    @pytest.mark.asyncio
    async def test_get_failover_chain_endpoint(self, async_client, async_db_session, async_sample_model):
        """Test GET /services/{service_id}/flavors/{flavor_id}/failover-chain."""
        # Create service and flavors
        service = Service(
            name="API Test Service",
            route="api-test-service",
            service_type="summary",
            is_active=True
        )
        async_db_session.add(service)
        await async_db_session.commit()

        flavor_a = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="primary",
            temperature=0.7,
            top_p=0.9
        )
        flavor_b = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="backup",
            temperature=0.5,
            top_p=0.8
        )
        async_db_session.add_all([flavor_a, flavor_b])
        await async_db_session.commit()

        # Set up chain
        flavor_a.failover_flavor_id = flavor_b.id
        await async_db_session.commit()

        # Call endpoint
        response = await async_client.get(
            f"/api/v1/services/{service.id}/flavors/{flavor_a.id}/failover-chain"
        )

        assert response.status_code == 200
        data = response.json()
        assert "chain" in data
        assert "max_depth" in data
        assert "has_cycle" in data
        assert len(data["chain"]) == 2
        assert data["chain"][0]["name"] == "primary"
        assert data["chain"][1]["name"] == "backup"

    @pytest.mark.asyncio
    async def test_get_failover_chain_not_found(self, async_client, async_db_session):
        """Test GET failover-chain with non-existent flavor returns 404."""
        fake_service_id = uuid4()
        fake_flavor_id = uuid4()

        response = await async_client.get(
            f"/api/v1/services/{fake_service_id}/flavors/{fake_flavor_id}/failover-chain"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_validate_failover_endpoint_valid(self, async_client, async_db_session, async_sample_model):
        """Test POST /services/{service_id}/flavors/{flavor_id}/validate-failover with valid chain."""
        service = Service(
            name="Validate Test Service",
            route="validate-test",
            service_type="summary",
            is_active=True
        )
        async_db_session.add(service)
        await async_db_session.commit()

        flavor_a = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="source",
            temperature=0.7,
            top_p=0.9
        )
        flavor_b = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="target",
            temperature=0.5,
            top_p=0.8
        )
        async_db_session.add_all([flavor_a, flavor_b])
        await async_db_session.commit()

        # Validate A -> B (valid)
        response = await async_client.post(
            f"/api/v1/services/{service.id}/flavors/{flavor_a.id}/validate-failover",
            json={"failover_flavor_id": str(flavor_b.id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["error"] is None
        assert len(data["chain_preview"]) >= 1

    @pytest.mark.asyncio
    async def test_validate_failover_endpoint_cycle(self, async_client, async_db_session, async_sample_model):
        """Test POST validate-failover detects cycle."""
        service = Service(
            name="Cycle Validate Service",
            route="cycle-validate",
            service_type="summary",
            is_active=True
        )
        async_db_session.add(service)
        await async_db_session.commit()

        flavor_a = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="flavor-a",
            temperature=0.7,
            top_p=0.9
        )
        flavor_b = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="flavor-b",
            temperature=0.5,
            top_p=0.8
        )
        async_db_session.add_all([flavor_a, flavor_b])
        await async_db_session.commit()

        # Set up: B -> A
        flavor_b.failover_flavor_id = flavor_a.id
        await async_db_session.commit()

        # Validate A -> B (would create cycle)
        response = await async_client.post(
            f"/api/v1/services/{service.id}/flavors/{flavor_a.id}/validate-failover",
            json={"failover_flavor_id": str(flavor_b.id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["error"] is not None
        assert "cycle" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_validate_failover_self_reference(self, async_client, async_db_session, async_sample_model):
        """Test POST validate-failover rejects self-reference."""
        service = Service(
            name="Self Ref Service",
            route="self-ref",
            service_type="summary",
            is_active=True
        )
        async_db_session.add(service)
        await async_db_session.commit()

        flavor = ServiceFlavor(
            service_id=service.id,
            model_id=async_sample_model.id,
            name="solo",
            temperature=0.7,
            top_p=0.9
        )
        async_db_session.add(flavor)
        await async_db_session.commit()

        # Validate self-reference
        response = await async_client.post(
            f"/api/v1/services/{service.id}/flavors/{flavor.id}/validate-failover",
            json={"failover_flavor_id": str(flavor.id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "self" in data["error"].lower()


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
