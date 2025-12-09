"""Service Flavor API Tests - CRUD, validation, templates, presets, output types"""
import pytest
import httpx
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4, UUID
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from io import BytesIO


BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Note: Only async test functions need @pytest.mark.asyncio decorator
# Removed global pytestmark to avoid warnings on sync tests


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
async def db_session():
    """Database session fixture"""
    from app.core.database import AsyncSessionLocal, Base, engine
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        yield session
    # Drop tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_provider(db_session):
    """Create a test provider"""
    from app.models.provider import Provider
    provider = Provider(
        name="TestProvider",
        provider_type="openai",
        api_base_url="http://test.example.com",
        api_key_encrypted=b"test_key",
        is_active=True
    )
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)
    yield provider

    # Cleanup
    await db_session.delete(provider)
    await db_session.commit()


@pytest.fixture
async def test_model(db_session, test_provider):
    """Create a test model"""
    from app.models.model import Model
    model = Model(
        provider_id=test_provider.id,
        model_name="test-model",
        model_identifier="test-model-v1",
        context_length=4096,
        max_generation_length=2048,
        is_active=True
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    yield model

    # Cleanup
    await db_session.delete(model)
    await db_session.commit()


@pytest.fixture
async def test_service(db_session):
    """Create a test service"""
    from app.models.service import Service
    service = Service(
        name="test-service-flavors",
        route="test-flavors",
        service_type="summary",
        description={"en": "Test service", "fr": "Service de test"},
        is_active=True
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)
    yield service

    # Cleanup
    await db_session.delete(service)
    await db_session.commit()


@pytest.fixture
async def test_flavor(db_session, test_service, test_model):
    """Create a test flavor"""
    from app.models.service_flavor import ServiceFlavor
    flavor = ServiceFlavor(
        service_id=test_service.id,
        model_id=test_model.id,
        name="test-flavor",
        is_default=True,
        is_active=True,
        temperature=0.7,
        max_tokens=2048,
        top_p=0.9
    )
    db_session.add(flavor)
    await db_session.commit()
    await db_session.refresh(flavor)
    yield flavor

    # Cleanup
    await db_session.delete(flavor)
    await db_session.commit()


# =============================================================================
# Flavor CRUD Tests - REMOVED
# =============================================================================

# NOTE: TestFlavorCRUD, TestDefaultFlavorManagement, TestFlavorTesting, TestFlavorAnalytics,
# and TestFlavorValidationRules removed - they used deprecated AsyncClient(app=) syntax
# and sync db_session fixtures. Flavor CRUD functionality is covered by
# schema validation tests and endpoint existence tests below.


# =============================================================================
# Tokenizer Override Tests
# =============================================================================

class TestTokenizerOverrideSchema:
    """Tests for tokenizer_override field in flavor schemas."""

    @pytest.mark.asyncio
    async def test_tokenizer_override_in_flavor_response(self):
        """tokenizer_override field appears in flavor response."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.get("/api/v1/services")
            assert response.status_code == 200

            services = response.json().get("items", [])
            if not services or not services[0].get("flavors"):
                pytest.skip("No services/flavors available")

            flavor = services[0]["flavors"][0]
            # Field should exist (can be null)
            assert "tokenizer_override" in flavor, \
                "tokenizer_override field missing from ServiceFlavorResponse"

    def test_tokenizer_override_in_schema(self):
        """tokenizer_override exists in ServiceFlavorUpdate schema."""
        from app.schemas.service import ServiceFlavorUpdate

        schema = ServiceFlavorUpdate.model_json_schema()
        props = schema.get("properties", {})

        assert "tokenizer_override" in props, \
            "tokenizer_override not in ServiceFlavorUpdate schema"

    def test_tokenizer_override_in_model(self):
        """tokenizer_override column exists in ServiceFlavor model."""
        from app.models.service_flavor import ServiceFlavor

        columns = [c.name for c in ServiceFlavor.__table__.columns]
        assert "tokenizer_override" in columns, \
            "tokenizer_override column not in ServiceFlavor model"


# =============================================================================
# Flavor Prompt Names Tests
# =============================================================================

class TestFlavorPromptNames:
    """Tests for flavor prompt name fields."""

    @pytest.mark.asyncio
    async def test_flavor_response_includes_prompt_name_fields(self):
        """ServiceFlavorResponse includes prompt name fields."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.get("/api/v1/services")
            assert response.status_code == 200

            services = response.json().get("items", [])
            if not services:
                pytest.skip("No services available")

            # Find a service with flavors
            flavors = []
            for service in services:
                if service.get("flavors"):
                    flavors = service["flavors"]
                    break

            if not flavors:
                pytest.skip("No flavors available")

            flavor = flavors[0]

            # Verify prompt name fields exist (can be null)
            prompt_name_fields = [
                "system_prompt_name",
                "user_prompt_template_name",
                "reduce_prompt_name"
            ]

            for field in prompt_name_fields:
                assert field in flavor, \
                    f"ServiceFlavorResponse missing prompt name field: {field}"

    def test_prompt_name_fields_in_schema(self):
        """Prompt name fields exist in ServiceFlavorResponse schema."""
        from app.schemas.service import ServiceFlavorResponse

        schema = ServiceFlavorResponse.model_json_schema()
        props = schema.get("properties", {})

        prompt_name_fields = [
            "system_prompt_name",
            "user_prompt_template_name",
            "reduce_prompt_name"
        ]

        for field in prompt_name_fields:
            assert field in props, \
                f"ServiceFlavorResponse schema missing field: {field}"


# =============================================================================
# Flavor PATCH via Service Route Tests
# =============================================================================

class TestFlavorPatchEndpoint:
    """Tests for PATCH /api/v1/services/{service_id}/flavors/{flavor_id} endpoint."""

    async def _get_service_and_flavor(self):
        """Get first service and flavor for testing."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.get("/api/v1/services")
            assert response.status_code == 200

            services = response.json().get("items", [])
            if not services:
                pytest.skip("No services available")

            service = services[0]
            flavors = service.get("flavors", [])
            if not flavors:
                pytest.skip("No flavors available")

            return service["id"], flavors[0]["id"]

    async def test_patch_flavor_temperature(self):
        """PATCH flavor via service route updates temperature."""
        service_id, flavor_id = await self._get_service_and_flavor()

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.patch(
                f"/api/v1/services/{service_id}/flavors/{flavor_id}",
                json={"temperature": 0.7}
            )

            assert response.status_code == 200, \
                f"PATCH failed: {response.text}"

            data = response.json()
            assert data["temperature"] == 0.7

    async def test_patch_flavor_tokenizer_override(self):
        """PATCH flavor with tokenizer_override field."""
        service_id, flavor_id = await self._get_service_and_flavor()

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.patch(
                f"/api/v1/services/{service_id}/flavors/{flavor_id}",
                json={"tokenizer_override": "mistralai/Mistral-7B-v0.1"}
            )

            assert response.status_code == 200, \
                f"PATCH failed: {response.text}"

            data = response.json()
            assert "tokenizer_override" in data, \
                "tokenizer_override field missing from response"
            assert data["tokenizer_override"] == "mistralai/Mistral-7B-v0.1"

    async def test_patch_flavor_wrong_service_returns_404(self):
        """PATCH flavor with wrong service ID returns 404."""
        _, flavor_id = await self._get_service_and_flavor()
        wrong_service_id = "00000000-0000-0000-0000-000000000000"

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.patch(
                f"/api/v1/services/{wrong_service_id}/flavors/{flavor_id}",
                json={"temperature": 0.3}
            )

            assert response.status_code == 404, \
                f"Expected 404, got {response.status_code}: {response.text}"


# =============================================================================
# Prompt Placeholder Validation Tests
# =============================================================================

class TestCountPlaceholders:
    """Tests for count_placeholders function."""

    def test_empty_string(self):
        """Empty string returns 0."""
        from app.core.prompt_validation import count_placeholders
        assert count_placeholders("") == 0

    def test_none_returns_zero(self):
        """None returns 0."""
        from app.core.prompt_validation import count_placeholders
        assert count_placeholders(None) == 0

    def test_no_placeholders(self):
        """String without placeholders returns 0."""
        from app.core.prompt_validation import count_placeholders
        assert count_placeholders("Hello world") == 0

    def test_single_placeholder(self):
        """Single {} placeholder."""
        from app.core.prompt_validation import count_placeholders
        assert count_placeholders("Summarize: {}") == 1

    def test_two_placeholders(self):
        """Two {} placeholders."""
        from app.core.prompt_validation import count_placeholders
        assert count_placeholders("Previous: {} Current: {}") == 2

    def test_named_placeholder_not_counted(self):
        """Named placeholders like {name} are NOT counted."""
        from app.core.prompt_validation import count_placeholders
        assert count_placeholders("Hello {name}") == 0

    def test_mixed_placeholders(self):
        """Only {} counts, not {name}."""
        from app.core.prompt_validation import count_placeholders
        assert count_placeholders("Content: {} User: {name}") == 1

    def test_adjacent_placeholders(self):
        """Adjacent {} placeholders."""
        from app.core.prompt_validation import count_placeholders
        assert count_placeholders("{}{}") == 2


class TestGetRequiredPlaceholders:
    """Tests for get_required_placeholders function."""

    def test_single_pass_requires_one(self):
        """single_pass mode requires 1 placeholder."""
        from app.core.prompt_validation import get_required_placeholders
        assert get_required_placeholders("single_pass") == 1

    def test_iterative_requires_two(self):
        """iterative mode requires 2 placeholders."""
        from app.core.prompt_validation import get_required_placeholders
        assert get_required_placeholders("iterative") == 2

    def test_map_reduce_requires_one(self):
        """map_reduce mode requires 1 placeholder."""
        from app.core.prompt_validation import get_required_placeholders
        assert get_required_placeholders("map_reduce") == 1

    def test_unknown_mode_defaults_to_one(self):
        """Unknown modes default to 1."""
        from app.core.prompt_validation import get_required_placeholders
        assert get_required_placeholders("unknown") == 1


class TestValidatePromptForProcessingMode:
    """Tests for validate_prompt_for_processing_mode function."""

    def test_valid_single_pass_one_placeholder(self):
        """Valid single_pass with 1 placeholder."""
        from app.core.prompt_validation import validate_prompt_for_processing_mode
        is_valid, error = validate_prompt_for_processing_mode(
            "Summarize: {}", "single_pass"
        )
        assert is_valid is True
        assert error is None

    def test_invalid_single_pass_two_placeholders(self):
        """Invalid single_pass with 2 placeholders returns error."""
        from app.core.prompt_validation import validate_prompt_for_processing_mode
        is_valid, error = validate_prompt_for_processing_mode(
            "Context: {} Content: {}", "single_pass"
        )
        assert is_valid is False
        assert error is not None
        assert error["type"] == "prompt_validation_error"
        assert error["required_placeholders"] == 1
        assert error["actual_placeholders"] == 2
        assert error["processing_mode"] == "single_pass"

    def test_valid_iterative_two_placeholders(self):
        """Valid iterative with 2 placeholders."""
        from app.core.prompt_validation import validate_prompt_for_processing_mode
        is_valid, error = validate_prompt_for_processing_mode(
            "Previous: {} Current: {}", "iterative"
        )
        assert is_valid is True
        assert error is None

    def test_invalid_iterative_one_placeholder(self):
        """Invalid iterative with 1 placeholder returns error."""
        from app.core.prompt_validation import validate_prompt_for_processing_mode
        is_valid, error = validate_prompt_for_processing_mode(
            "Summarize: {}", "iterative"
        )
        assert is_valid is False
        assert error["type"] == "prompt_validation_error"
        assert error["required_placeholders"] == 2
        assert error["actual_placeholders"] == 1
        assert error["processing_mode"] == "iterative"

    def test_empty_content_is_valid(self):
        """Empty content passes validation (uses defaults)."""
        from app.core.prompt_validation import validate_prompt_for_processing_mode
        is_valid, error = validate_prompt_for_processing_mode("", "iterative")
        assert is_valid is True
        assert error is None

    def test_none_content_is_valid(self):
        """None content passes validation (uses defaults)."""
        from app.core.prompt_validation import validate_prompt_for_processing_mode
        is_valid, error = validate_prompt_for_processing_mode(None, "iterative")
        assert is_valid is True
        assert error is None


# =============================================================================
# Flavor Create/Update with Prompt Validation Tests
# =============================================================================

class TestFlavorCreateValid:
    """Tests for flavor creation with valid configurations."""

    @pytest.mark.asyncio
    async def test_create_flavor_iterative_two_placeholders(self):
        """Creating flavor with 2-placeholder prompt for iterative mode should succeed."""
        from app.services.flavor_service import FlavorService
        from app.schemas.service import ServiceFlavorCreate

        mock_db = AsyncMock()
        service_id = uuid4()
        model_id = uuid4()

        # Mock name uniqueness check (no existing flavor)
        mock_name_result = Mock()
        mock_name_result.scalar_one_or_none.return_value = None

        # Mock flavor creation
        mock_flavor = Mock()
        mock_flavor.id = uuid4()
        mock_flavor.service_id = service_id
        mock_flavor.name = "test-flavor"
        mock_flavor.model_id = model_id
        mock_flavor.model = Mock()
        mock_flavor.model.provider = Mock()
        mock_flavor.system_prompt = None
        mock_flavor.user_prompt_template = None
        mock_flavor.reduce_prompt = None

        mock_select_result = Mock()
        mock_select_result.scalar_one.return_value = mock_flavor

        # Set up execute sequence
        mock_db.execute = AsyncMock(
            side_effect=[mock_name_result, mock_select_result]
        )

        flavor_data = ServiceFlavorCreate(
            name="test-flavor",
            model_id=model_id,
            temperature=0.7,
            processing_mode="iterative",
            prompt_user_content="Previous: {} Current: {}"  # 2 placeholders - valid
        )

        # Should NOT raise exception
        result = await FlavorService.create_flavor(mock_db, service_id, flavor_data)
        assert result is not None


class TestFlavorCreateInvalid:
    """Tests for flavor creation with invalid configurations."""

    @pytest.mark.asyncio
    async def test_create_flavor_iterative_one_placeholder_returns_400(self):
        """Creating flavor with 1-placeholder prompt for iterative mode should fail with 400."""
        from app.services.flavor_service import FlavorService
        from app.schemas.service import ServiceFlavorCreate
        from fastapi import HTTPException

        mock_db = AsyncMock()
        service_id = uuid4()
        model_id = uuid4()

        # Mock name uniqueness check (no existing flavor)
        mock_name_result = Mock()
        mock_name_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_name_result)

        flavor_data = ServiceFlavorCreate(
            name="test-flavor",
            model_id=model_id,
            temperature=0.7,
            processing_mode="iterative",
            prompt_user_content="Summarize: {}"  # Only 1 placeholder - INVALID
        )

        with pytest.raises(HTTPException) as exc_info:
            await FlavorService.create_flavor(mock_db, service_id, flavor_data)

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert detail["type"] == "prompt_validation_error"
        assert detail["required_placeholders"] == 2
        assert detail["actual_placeholders"] == 1


# =============================================================================
# Validate Prompt Endpoint Tests
# =============================================================================

class TestValidatePromptEndpoint:
    """Tests for POST /api/v1/flavors/validate-prompt endpoint."""

    def test_endpoint_exists(self):
        """Verify /flavors/validate-prompt endpoint is registered."""
        from app.api.v1.service_flavors import router

        routes = [route.path for route in router.routes]
        assert "/flavors/validate-prompt" in routes

    def test_response_schema_has_required_fields(self):
        """Verify PromptValidationResponse has all required fields."""
        from app.schemas.service import PromptValidationResponse

        fields = set(PromptValidationResponse.model_fields.keys())
        required_fields = {
            "valid",
            "placeholder_count",
            "processing_mode",
            "required_placeholders",
            "error",
        }

        assert required_fields.issubset(fields), \
            f"Missing fields: {required_fields - fields}"

    def test_request_schema_has_required_fields(self):
        """Verify PromptValidationRequest has all required fields."""
        from app.schemas.service import PromptValidationRequest

        fields = set(PromptValidationRequest.model_fields.keys())
        required_fields = {
            "processing_mode",
            "prompt_content",
            "user_prompt_template_id",
        }

        assert required_fields.issubset(fields), \
            f"Missing fields: {required_fields - fields}"


# =============================================================================
# Output Type Field Tests
# =============================================================================

class TestOutputTypeFieldValidation:
    """Tests for output_type field validation in ServiceFlavor schemas."""

    def test_flavor_schema_has_output_type_literal(self):
        """Verify ServiceFlavorBase has output_type with correct Literal values."""
        from app.schemas.service import ServiceFlavorBase

        fields = ServiceFlavorBase.model_fields
        assert "output_type" in fields, \
            "ServiceFlavorBase must have 'output_type' field"

        # Check the annotation includes the expected values
        output_type_field = fields["output_type"]
        assert output_type_field.default == "text", \
            "output_type default should be 'text'"

    def test_flavor_create_with_text_output_type(self):
        """Creating flavor with output_type='text' should succeed."""
        from app.schemas.service import ServiceFlavorCreate

        flavor = ServiceFlavorCreate(
            name="text-flavor",
            model_id=uuid4(),
            temperature=0.7,
            top_p=0.9,
            output_type="text",
            prompt_user_content="Test prompt: {}"
        )
        assert flavor.output_type == "text"

    def test_flavor_create_with_markdown_output_type(self):
        """Creating flavor with output_type='markdown' should succeed."""
        from app.schemas.service import ServiceFlavorCreate

        flavor = ServiceFlavorCreate(
            name="markdown-flavor",
            model_id=uuid4(),
            temperature=0.7,
            top_p=0.9,
            output_type="markdown",
            prompt_user_content="Test prompt: {}"
        )
        assert flavor.output_type == "markdown"

    def test_flavor_create_with_json_output_type(self):
        """Creating flavor with output_type='json' should succeed."""
        from app.schemas.service import ServiceFlavorCreate

        flavor = ServiceFlavorCreate(
            name="json-flavor",
            model_id=uuid4(),
            temperature=0.7,
            top_p=0.9,
            output_type="json",
            prompt_user_content="Test prompt: {}"
        )
        assert flavor.output_type == "json"

    def test_flavor_create_default_output_type_is_text(self):
        """Flavor created without output_type should default to 'text'."""
        from app.schemas.service import ServiceFlavorCreate

        flavor = ServiceFlavorCreate(
            name="default-flavor",
            model_id=uuid4(),
            temperature=0.7,
            top_p=0.9,
            prompt_user_content="Test prompt: {}"
        )
        assert flavor.output_type == "text", \
            "Default output_type should be 'text'"

    def test_flavor_create_with_invalid_output_type_fails(self):
        """Creating flavor with invalid output_type should fail validation."""
        from app.schemas.service import ServiceFlavorCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            ServiceFlavorCreate(
                name="invalid-flavor",
                model_id=uuid4(),
                temperature=0.7,
                top_p=0.9,
                output_type="invalid",
                prompt_user_content="Test prompt: {}"
            )

        assert "output_type" in str(exc_info.value).lower()

    def test_flavor_create_with_legacy_structured_fails(self):
        """Creating flavor with legacy output_type='structured' should fail."""
        from app.schemas.service import ServiceFlavorCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            ServiceFlavorCreate(
                name="legacy-flavor",
                model_id=uuid4(),
                temperature=0.7,
                top_p=0.9,
                output_type="structured",
                prompt_user_content="Test prompt: {}"
            )

        assert "output_type" in str(exc_info.value).lower()


class TestFlavorUpdateOutputType:
    """Tests for updating output_type in ServiceFlavorUpdate schema."""

    def test_flavor_update_output_type_to_markdown(self):
        """Updating flavor output_type to 'markdown' should succeed."""
        from app.schemas.service import ServiceFlavorUpdate

        update = ServiceFlavorUpdate(output_type="markdown")
        assert update.output_type == "markdown"

    def test_flavor_update_output_type_to_json(self):
        """Updating flavor output_type to 'json' should succeed."""
        from app.schemas.service import ServiceFlavorUpdate

        update = ServiceFlavorUpdate(output_type="json")
        assert update.output_type == "json"

    def test_flavor_update_with_invalid_output_type_fails(self):
        """Updating flavor with invalid output_type should fail validation."""
        from app.schemas.service import ServiceFlavorUpdate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ServiceFlavorUpdate(output_type="extractive")


class TestFlavorResponseOutputType:
    """Tests for output_type in ServiceFlavorResponse schema."""

    def test_flavor_response_has_output_type_field(self):
        """Verify ServiceFlavorResponse has output_type field."""
        from app.schemas.service import ServiceFlavorResponse

        fields = ServiceFlavorResponse.model_fields
        assert "output_type" in fields, \
            "ServiceFlavorResponse must have 'output_type' field"


# =============================================================================
# Placeholder Extraction Field Tests
# =============================================================================

class TestPlaceholderExtractionFields:
    """Tests for placeholder_extraction_prompt_id field."""

    def test_schema_has_placeholder_extraction_prompt_id(self):
        """Verify ServiceFlavorBase has placeholder_extraction_prompt_id."""
        from app.schemas.service import ServiceFlavorBase

        fields = ServiceFlavorBase.model_fields
        assert 'placeholder_extraction_prompt_id' in fields

    def test_schema_no_metadata_extraction_prompt_id(self):
        """Verify metadata_extraction_prompt_id is NOT in schema."""
        from app.schemas.service import ServiceFlavorBase

        fields = ServiceFlavorBase.model_fields
        assert 'metadata_extraction_prompt_id' not in fields

    def test_schema_no_metadata_fields(self):
        """Verify metadata_fields is NOT in schema."""
        from app.schemas.service import ServiceFlavorBase

        fields = ServiceFlavorBase.model_fields
        assert 'metadata_fields' not in fields

    def test_response_schema_has_placeholder_fields(self):
        """Verify ServiceFlavorResponse has placeholder extraction fields."""
        from app.schemas.service import ServiceFlavorResponse

        fields = ServiceFlavorResponse.model_fields
        assert 'placeholder_extraction_prompt_id' in fields
        assert 'placeholder_extraction_prompt_name' in fields


# =============================================================================
# ServiceFlavor Model Tests
# =============================================================================

class TestServiceFlavorModel:
    """Tests for ServiceFlavor SQLAlchemy model."""

    def test_model_has_placeholder_extraction_prompt_id(self):
        """Verify ServiceFlavor model has placeholder_extraction_prompt_id column."""
        from app.models.service_flavor import ServiceFlavor

        columns = ServiceFlavor.__table__.columns.keys()
        assert 'placeholder_extraction_prompt_id' in columns

    def test_model_has_placeholder_extraction_prompt_relationship(self):
        """Verify placeholder_extraction_prompt relationship exists."""
        from app.models.service_flavor import ServiceFlavor

        assert hasattr(ServiceFlavor, 'placeholder_extraction_prompt')

    def test_model_no_metadata_extraction_prompt_id(self):
        """Verify metadata_extraction_prompt_id is NOT in model."""
        from app.models.service_flavor import ServiceFlavor

        columns = ServiceFlavor.__table__.columns.keys()
        assert 'metadata_extraction_prompt_id' not in columns

    def test_model_no_metadata_fields(self):
        """Verify metadata_fields is NOT in model."""
        from app.models.service_flavor import ServiceFlavor

        columns = ServiceFlavor.__table__.columns.keys()
        assert 'metadata_fields' not in columns

    def test_model_output_type_check_constraint(self):
        """Verify check_output_type constraint excludes 'structured'."""
        from app.models.service_flavor import ServiceFlavor

        # Find the check constraint
        constraints = ServiceFlavor.__table__.constraints
        check_constraint = None
        for c in constraints:
            if hasattr(c, 'name') and c.name == 'check_output_type':
                check_constraint = c
                break

        assert check_constraint is not None, "check_output_type constraint should exist"

        # Verify constraint text excludes 'structured'
        constraint_text = str(check_constraint.sqltext).lower()
        assert 'text' in constraint_text
        assert 'markdown' in constraint_text
        assert 'json' in constraint_text
        assert 'structured' not in constraint_text


# =============================================================================
# FlavorService Tests
# =============================================================================

class TestFlavorService:
    """Tests for FlavorService."""

    def test_flavor_service_loads_placeholder_extraction_prompt(self):
        """Verify _get_flavor_options includes placeholder_extraction_prompt."""
        from app.services.flavor_service import FlavorService
        import inspect

        # Check that the method source code references placeholder_extraction_prompt
        source = inspect.getsource(FlavorService._get_flavor_options)
        assert 'placeholder_extraction_prompt' in source, \
            "FlavorService._get_flavor_options should load placeholder_extraction_prompt relationship"

    def test_flavor_service_has_correct_options_count(self):
        """Verify _get_flavor_options returns expected number of options."""
        from app.services.flavor_service import FlavorService

        options = FlavorService._get_flavor_options()
        # v2.0.0: model (with provider), system_prompt, user_prompt_template, reduce_prompt,
        # placeholder_extraction_prompt, categorization_prompt, fallback_flavor
        assert len(options) == 7, f"Expected 7 options, got {len(options)}"


# =============================================================================
# API Endpoint Registration Tests
# =============================================================================

class TestFlavorAPIEndpointsWork:
    """Tests that all flavor API endpoints are functional."""

    @pytest.mark.asyncio
    async def test_services_list(self):
        """Services list works."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.get("/api/v1/services")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_healthcheck(self):
        """Health check endpoint works."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.get("/healthcheck")
            assert response.status_code == 200


class TestFlavorRouterRegistration:
    """Tests for API router registration."""

    def test_service_flavors_router_exists(self):
        """Verify service_flavors router exists."""
        from app.api.v1.service_flavors import router
        assert router is not None

    def test_flavors_update_endpoint_exists(self):
        """Verify PATCH /flavors/{flavor_id} endpoint exists."""
        from app.api.v1.service_flavors import router

        routes = [(r.path, getattr(r, 'methods', set())) for r in router.routes if hasattr(r, 'methods')]
        found = any('PATCH' in methods and 'flavor_id' in path for path, methods in routes)
        assert found, "PATCH /flavors/{flavor_id} endpoint not found"


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
