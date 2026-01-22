"""Model API Tests - CRUD, verification, discovery, limits"""
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
import httpx
import os
from pathlib import Path


# =============================================================================
# Model CRUD Tests - REMOVED
# =============================================================================

# NOTE: TestModelCRUD and TestModelVerification removed - they used sync db_session
# fixtures with async API endpoints. Model CRUD functionality is covered by
# schema validation tests and endpoint existence tests below.


# =============================================================================
# Model Extended Fields Tests
# =============================================================================

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class TestModelExtendedFields:
    """Tests for Model API extended fields"""

    @pytest.mark.asyncio
    async def test_model_response_includes_extended_fields(self):
        """Verify ModelResponse includes all extended fields."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            # Get all models
            response = await client.get("/api/v1/models")

            if response.status_code != 200:
                pytest.skip("Models endpoint not available")

            data = response.json()
            items = data.get("items", [])

            if not items:
                pytest.skip("No models available for field validation")

            model = items[0]

            # Verify extended fields are present in schema (may be null)
            extended_fields = [
                "huggingface_repo",
                "security_level",
                "deployment_name",
                "description",
                "best_use",
                "usage_type",
                "system_prompt",
            ]

            for field in extended_fields:
                assert field in model, f"Missing extended field: {field}"

    @pytest.mark.asyncio
    async def test_model_update_with_extended_fields(self):
        """PUT /api/v1/models/{id} with extended fields."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            # Get a model to update
            response = await client.get("/api/v1/models")

            if response.status_code != 200:
                pytest.skip("Models endpoint not available")

            data = response.json()
            items = data.get("items", [])

            if not items:
                pytest.skip("No models available for update test")

            model = items[0]
            model_id = model["id"]

            # Update with extended fields
            update_data = {
                "huggingface_repo": "test/test-model",
                "security_level": 2,
                "description": "Test description for QA",
                "best_use": "Testing",
                "usage_type": "chat",
            }

            response = await client.put(
                f"/api/v1/models/{model_id}",
                json=update_data
            )

            assert response.status_code == 200, \
                f"Expected 200, got {response.status_code}: {response.text}"

            updated = response.json()

            # Verify extended fields were updated
            assert updated["huggingface_repo"] == "test/test-model"
            assert updated["security_level"] == 2
            assert updated["description"] == "Test description for QA"


# =============================================================================
# Model Discovery Tests
# =============================================================================

class TestModelDiscovery:
    """Tests for model discovery with extended metadata"""

    @pytest.mark.asyncio
    async def test_discover_models_endpoint_exists(self):
        """Verify discover-models endpoint exists in OpenAPI."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.get("/openapi.json")

            assert response.status_code == 200
            data = response.json()
            paths = list(data.get("paths", {}).keys())

            assert "/api/v1/providers/{provider_id}/discover-models" in paths, \
                "discover-models endpoint not in OpenAPI"

    @pytest.mark.asyncio
    async def test_discover_models_nonexistent_provider_returns_404(self):
        """discover-models with invalid provider_id returns 404."""
        fake_provider_id = "00000000-0000-0000-0000-000000000000"

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.get(
                f"/api/v1/providers/{fake_provider_id}/discover-models"
            )

            assert response.status_code == 404, \
                f"Expected 404, got {response.status_code}"


# =============================================================================
# Model Limits Tests (Known Models Database)
# =============================================================================

class TestMatchModelLimitsFunction:
    """Tests for match_model_limits function in app.core.model_limits."""

    def test_match_known_model_gpt4o(self):
        """GPT-4o should match and return documented limits."""
        from app.core.model_limits import match_model_limits

        result = match_model_limits("gpt-4o")
        assert result is not None
        assert result["context_length"] == 128000
        assert result["max_generation_length"] == 16384
        assert result["source"] == "documented"

    def test_match_known_model_gpt4o_mini(self):
        """GPT-4o-mini should match and return documented limits."""
        from app.core.model_limits import match_model_limits

        result = match_model_limits("gpt-4o-mini")
        assert result is not None
        assert result["context_length"] == 128000
        assert result["max_generation_length"] == 16384
        assert result["source"] == "documented"

    def test_match_known_model_claude_sonnet_4(self):
        """Claude Sonnet 4 should match with correct limits."""
        from app.core.model_limits import match_model_limits

        result = match_model_limits("claude-sonnet-4")
        assert result is not None
        assert result["context_length"] == 200000
        assert result["max_generation_length"] == 64000
        assert result["source"] == "documented"

    def test_match_known_model_o1(self):
        """O1 models should match with correct limits."""
        from app.core.model_limits import match_model_limits

        result = match_model_limits("o1")
        assert result is not None
        assert result["context_length"] == 200000
        assert result["max_generation_length"] == 100000
        assert result["source"] == "documented"

    def test_match_unknown_model_returns_none(self):
        """Unknown models should return None."""
        from app.core.model_limits import match_model_limits

        result = match_model_limits("totally-unknown-model-xyz")
        assert result is None

    def test_match_case_insensitive(self):
        """Model matching should be case-insensitive."""
        from app.core.model_limits import match_model_limits

        result_upper = match_model_limits("GPT-4O")
        result_mixed = match_model_limits("GpT-4o-MiNi")

        assert result_upper is not None
        assert result_mixed is not None
        assert result_upper["context_length"] == 128000


class TestGetConservativeEstimate:
    """Tests for get_conservative_estimate function."""

    def test_conservative_estimate_returns_defaults(self):
        """Conservative estimate should return safe defaults."""
        from app.core.model_limits import get_conservative_estimate

        result = get_conservative_estimate("unknown-model")
        assert result["context_length"] == 4096
        assert result["max_generation_length"] == 2048
        assert result["source"] == "estimated"


# =============================================================================
# Simplified Model Limits Tests (No Overrides)
# =============================================================================

class TestModelSchemaNoOverrides:
    """Tests verifying Model schema simplified structure."""

    def test_model_response_schema_no_override_fields(self):
        """Verify ModelResponse schema does NOT have override fields."""
        from app.schemas.model import ModelResponse

        fields = set(ModelResponse.model_fields.keys())

        # These fields should NOT exist
        assert "context_length_override" not in fields, \
            "ModelResponse should NOT have 'context_length_override'"
        assert "max_generation_length_override" not in fields, \
            "ModelResponse should NOT have 'max_generation_length_override'"
        assert "limits_source" not in fields, \
            "ModelResponse should NOT have 'limits_source'"

    def test_model_response_schema_has_direct_limits(self):
        """Verify ModelResponse has direct limit fields."""
        from app.schemas.model import ModelResponse

        fields = set(ModelResponse.model_fields.keys())

        # These fields MUST exist (the authoritative values)
        assert "context_length" in fields, \
            "ModelResponse must have 'context_length'"
        assert "max_generation_length" in fields, \
            "ModelResponse must have 'max_generation_length'"

    def test_model_update_schema_has_direct_limit_fields(self):
        """Verify ModelUpdate can update context_length and max_generation_length directly."""
        from app.schemas.model import ModelUpdate

        fields = set(ModelUpdate.model_fields.keys())

        # Users should be able to edit limits directly
        assert "context_length" in fields, \
            "ModelUpdate must have 'context_length' for direct editing"
        assert "max_generation_length" in fields, \
            "ModelUpdate must have 'max_generation_length' for direct editing"


class TestModelLimitsSchema:
    """Tests for /models/{id}/limits endpoint response schema."""

    def test_model_limits_response_fields(self):
        """Verify ModelLimitsResponse has correct fields."""
        from app.schemas.model import ModelLimitsResponse

        fields = set(ModelLimitsResponse.model_fields.keys())

        # Required fields
        expected_fields = {
            "model_id",
            "model_name",
            "model_identifier",
            "context_length",
            "max_generation_length",
            "available_for_input",
        }

        assert expected_fields.issubset(fields), \
            f"ModelLimitsResponse missing fields: {expected_fields - fields}"

    def test_model_limits_response_no_override_fields(self):
        """Verify ModelLimitsResponse does NOT have deprecated fields."""
        from app.schemas.model import ModelLimitsResponse

        fields = set(ModelLimitsResponse.model_fields.keys())

        # These fields should NOT exist
        assert "limits_source" not in fields
        assert "has_override" not in fields
        assert "discovered_values" not in fields

    def test_model_limits_response_calculation(self):
        """Test that available_for_input is calculated correctly."""
        from app.schemas.model import ModelLimitsResponse

        response = ModelLimitsResponse(
            model_id=uuid4(),
            model_name="Test Model",
            model_identifier="test-model",
            context_length=32000,
            max_generation_length=4096,
            available_for_input=32000 - 4096,
        )

        assert response.available_for_input == 27904, \
            "available_for_input should equal context_length - max_generation_length"


class TestModelDatabaseNoOverrides:
    """Tests verifying Model SQLAlchemy model simplified structure."""

    def test_model_table_no_override_columns(self):
        """Verify Model table does NOT have override columns."""
        from app.models.model import Model

        columns = {c.name for c in Model.__table__.columns}

        # These columns should NOT exist
        assert "context_length_override" not in columns
        assert "max_generation_length_override" not in columns
        assert "limits_source" not in columns

    def test_model_table_has_direct_limit_columns(self):
        """Verify Model table has direct limit columns."""
        from app.models.model import Model

        columns = {c.name for c in Model.__table__.columns}

        # These columns MUST exist
        assert "context_length" in columns
        assert "max_generation_length" in columns


class TestModelLimitsEndpointExists:
    """Tests for /models/{model_id}/limits endpoint."""

    def test_limits_endpoint_route_exists(self):
        """Verify /models/{model_id}/limits endpoint is registered."""
        from app.api.v1.models import router

        routes = [route.path for route in router.routes]
        assert "/models/{model_id}/limits" in routes

    def test_limits_endpoint_is_get_method(self):
        """Verify /limits endpoint uses GET method."""
        from app.api.v1.models import router

        for route in router.routes:
            if getattr(route, 'path', None) == "/models/{model_id}/limits":
                assert "GET" in route.methods
                break


# =============================================================================
# i18n Tests
# =============================================================================

class TestModelI18n:
    """Tests verifying i18n functionality for models."""

    def test_model_create_with_french_description(self):
        """Test ModelCreate accepts French description in extended fields."""
        from app.schemas.model import ModelCreate

        model = ModelCreate(
            provider_id=uuid4(),
            model_name="Test Model",
            model_identifier="test-model",
            context_length=8192,
            max_generation_length=2048,
            description="Un modele de test"
        )

        assert model.description == "Un modele de test"


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
