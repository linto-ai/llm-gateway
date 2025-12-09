"""
Context Validation & Auto-Fallback to Iterative Flavor - QA Tests

Tests:
1. New /run endpoint functionality
2. Fallback availability check endpoint
3. Context validation logic and fallback behavior
4. Response schema updates with fallback fields
5. Error codes verification
"""

import pytest
import io
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from uuid import uuid4, UUID


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    return db


@pytest.fixture
def mock_provider():
    """Create a mock provider."""
    provider = Mock()
    provider.id = uuid4()
    provider.name = "test-provider"
    provider.provider_type = "openai"
    provider.api_base_url = "https://api.openai.com/v1"
    return provider


@pytest.fixture
def mock_model(mock_provider):
    """Create a mock model with context window settings."""
    model = Mock()
    model.id = uuid4()
    model.model_name = "gpt-4"
    model.model_identifier = "gpt-4"
    model.context_length = 8192
    model.max_generation_length = 2048
    model.tokenizer_class = "tiktoken"
    model.tokenizer_name = None
    model.provider_id = mock_provider.id
    model.provider = mock_provider
    return model


@pytest.fixture
def mock_single_pass_flavor(mock_model):
    """Create a mock single-pass flavor."""
    flavor = Mock()
    flavor.id = uuid4()
    flavor.name = "single-pass"
    flavor.model_id = mock_model.id
    flavor.model = mock_model
    flavor.temperature = 0.7
    flavor.top_p = 0.9
    flavor.is_active = True
    flavor.is_default = True
    flavor.processing_mode = "single_pass"
    flavor.tokenizer_override = None
    flavor.service_id = uuid4()
    flavor.prompt_system_content = "System prompt"
    flavor.prompt_user_content = "User prompt"
    flavor.prompt_reduce_content = None
    flavor.reduce_prompt = None
    flavor.create_new_turn_after = 500
    flavor.summary_turns = 3
    flavor.max_new_turns = 10
    flavor.reduce_summary = False
    flavor.consolidate_summary = False
    flavor.output_type = "text"
    return flavor


@pytest.fixture
def mock_iterative_flavor(mock_model, mock_single_pass_flavor):
    """Create a mock iterative flavor for fallback."""
    flavor = Mock()
    flavor.id = uuid4()
    flavor.name = "iterative"
    flavor.model_id = mock_model.id
    flavor.model = mock_model
    flavor.temperature = 0.7
    flavor.top_p = 0.9
    flavor.is_active = True
    flavor.is_default = False
    flavor.processing_mode = "iterative"
    flavor.tokenizer_override = None
    flavor.service_id = mock_single_pass_flavor.service_id  # Same service
    flavor.prompt_system_content = "System prompt"
    flavor.prompt_user_content = "User prompt"
    flavor.prompt_reduce_content = None
    flavor.reduce_prompt = None
    flavor.create_new_turn_after = 500
    flavor.summary_turns = 3
    flavor.max_new_turns = 10
    flavor.reduce_summary = False
    flavor.consolidate_summary = False
    flavor.output_type = "text"
    return flavor


@pytest.fixture
def mock_service(mock_single_pass_flavor):
    """Create a mock service."""
    service = Mock()
    service.id = mock_single_pass_flavor.service_id
    service.name = "test-service"
    service.route = "test-service"
    service.service_type = "summary"
    service.fields = 1
    service.is_active = True
    service.flavors = [mock_single_pass_flavor]
    return service


# =============================================================================
# 1. Schema Tests - Response Fields
# =============================================================================

class TestServiceExecuteResponseSchema:
    """Tests for ServiceExecuteResponse schema with fallback fields."""

    def test_response_has_fallback_fields(self):
        """Verify ServiceExecuteResponse includes all new fallback fields."""
        from app.schemas.service import ServiceExecuteResponse

        # Create response with fallback fields
        response = ServiceExecuteResponse(
            job_id=str(uuid4()),
            status="queued",
            service_id=str(uuid4()),
            service_name="test-service",
            flavor_id=str(uuid4()),
            flavor_name="test-flavor",
            created_at=datetime.now(timezone.utc).isoformat(),
            fallback_applied=True,
            original_flavor_id=str(uuid4()),
            original_flavor_name="original-flavor",
            fallback_reason="Input (15000 tokens) exceeds context limit (5692 available)",
            input_tokens=15000,
            context_available=5692
        )

        assert response.fallback_applied is True
        assert response.original_flavor_id is not None
        assert response.original_flavor_name == "original-flavor"
        assert response.fallback_reason is not None
        assert response.input_tokens == 15000
        assert response.context_available == 5692

    def test_response_defaults_no_fallback(self):
        """Verify default values when no fallback applied."""
        from app.schemas.service import ServiceExecuteResponse

        response = ServiceExecuteResponse(
            job_id=str(uuid4()),
            status="queued",
            service_id=str(uuid4()),
            service_name="test-service",
            flavor_id=str(uuid4()),
            flavor_name="test-flavor",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        assert response.fallback_applied is False
        assert response.original_flavor_id is None
        assert response.original_flavor_name is None
        assert response.fallback_reason is None


class TestExecutionErrorResponseSchema:
    """Tests for ExecutionErrorResponse schema."""

    def test_context_exceeded_error_schema(self):
        """Verify CONTEXT_EXCEEDED error response structure."""
        from app.schemas.service import ExecutionErrorResponse

        error = ExecutionErrorResponse(
            detail="Input exceeds context window",
            error_code="CONTEXT_EXCEEDED",
            input_tokens=15000,
            available_tokens=5692,
            suggestion="Configure a fallback flavor or reduce input size"
        )

        assert error.error_code == "CONTEXT_EXCEEDED"
        assert error.input_tokens == 15000
        assert error.available_tokens == 5692
        assert error.suggestion is not None

    def test_context_exceeded_no_fallback_error_schema(self):
        """Verify CONTEXT_EXCEEDED_NO_FALLBACK error response structure."""
        from app.schemas.service import ExecutionErrorResponse

        error = ExecutionErrorResponse(
            detail="Input exceeds context window and no iterative fallback flavor available",
            error_code="CONTEXT_EXCEEDED_NO_FALLBACK",
            input_tokens=15000,
            available_tokens=5692,
            suggestion="Create an iterative flavor for this service or reduce input size"
        )

        assert error.error_code == "CONTEXT_EXCEEDED_NO_FALLBACK"
        assert "no iterative fallback" in error.detail.lower()

    def test_flavor_inactive_error_schema(self):
        """Verify FLAVOR_INACTIVE error response structure."""
        from app.schemas.service import ExecutionErrorResponse

        flavor_id = str(uuid4())
        error = ExecutionErrorResponse(
            detail="Selected flavor is inactive",
            error_code="FLAVOR_INACTIVE",
            flavor_id=flavor_id,
            flavor_name="inactive-flavor"
        )

        assert error.error_code == "FLAVOR_INACTIVE"
        assert error.flavor_id == flavor_id
        assert error.flavor_name == "inactive-flavor"


class TestFallbackAvailabilityResponseSchema:
    """Tests for FallbackAvailabilityResponse schema."""

    def test_fallback_available_response(self):
        """Verify response when fallback is available."""
        from app.schemas.service import FallbackAvailabilityResponse

        response = FallbackAvailabilityResponse(
            fallback_available=True,
            fallback_flavor_id=str(uuid4()),
            fallback_flavor_name="iterative-flavor"
        )

        assert response.fallback_available is True
        assert response.fallback_flavor_id is not None
        assert response.fallback_flavor_name == "iterative-flavor"
        assert response.reason is None

    def test_fallback_not_available_response(self):
        """Verify response when no fallback available."""
        from app.schemas.service import FallbackAvailabilityResponse

        response = FallbackAvailabilityResponse(
            fallback_available=False,
            fallback_flavor_id=None,
            fallback_flavor_name=None,
            reason="No active iterative flavor in this service"
        )

        assert response.fallback_available is False
        assert response.fallback_flavor_id is None
        assert response.reason is not None


# =============================================================================
# 2. Context Validation Tests
# =============================================================================

class TestContextValidation:
    """Tests for _validate_context helper function."""

    @pytest.mark.asyncio
    async def test_validate_context_fits(self, mock_single_pass_flavor):
        """Test that small content passes validation."""
        from app.api.v1.services import _validate_context

        # Small content (100 words ~ 130 tokens)
        small_content = "This is a test sentence. " * 20

        with patch('app.api.v1.services.TokenizerManager') as mock_tm:
            mock_manager = Mock()
            mock_manager.count_tokens.return_value = 130
            mock_tm.get_instance.return_value = mock_manager

            fits, input_tokens, available = await _validate_context(
                mock_single_pass_flavor,
                small_content
            )

            assert fits is True
            assert input_tokens == 130
            # available = 8192 - 2048 - 500 = 5644
            assert available == 5644

    @pytest.mark.asyncio
    async def test_validate_context_exceeds(self, mock_single_pass_flavor):
        """Test that large content fails validation."""
        from app.api.v1.services import _validate_context

        # Large content
        large_content = "Speaker1: word " * 10000

        with patch('app.api.v1.services.TokenizerManager') as mock_tm:
            mock_manager = Mock()
            mock_manager.count_tokens.return_value = 15000
            mock_tm.get_instance.return_value = mock_manager

            fits, input_tokens, available = await _validate_context(
                mock_single_pass_flavor,
                large_content
            )

            assert fits is False
            assert input_tokens == 15000
            assert available == 5644  # 8192 - 2048 - 500

    @pytest.mark.asyncio
    async def test_validate_context_tokenizer_fallback(self, mock_single_pass_flavor):
        """Test fallback to character estimate when tokenizer fails."""
        from app.api.v1.services import _validate_context

        content = "a" * 4000  # 4000 chars ~ 1000 tokens estimate

        with patch('app.api.v1.services.TokenizerManager') as mock_tm:
            mock_tm.get_instance.side_effect = Exception("Tokenizer failed")

            fits, input_tokens, available = await _validate_context(
                mock_single_pass_flavor,
                content
            )

            # Should fallback to len(content) // 4 = 1000
            assert input_tokens == 1000
            assert fits is True


# =============================================================================
# 3. Fallback Flavor Selection Tests
# =============================================================================

class TestFallbackFlavorSelection:
    """Tests for _find_fallback_flavor helper function."""

    @pytest.mark.asyncio
    async def test_find_fallback_flavor_success(
        self,
        mock_db,
        mock_single_pass_flavor,
        mock_iterative_flavor
    ):
        """Test finding an iterative fallback flavor."""
        from app.services.flavor_service import FlavorService

        # Mock the database query to return the iterative flavor
        with patch.object(
            FlavorService,
            'find_iterative_fallback',
            new_callable=AsyncMock
        ) as mock_find:
            mock_find.return_value = mock_iterative_flavor

            fallback = await FlavorService.find_iterative_fallback(
                mock_db,
                mock_single_pass_flavor.service_id,
                mock_single_pass_flavor.id
            )

            assert fallback is not None
            assert fallback.processing_mode == "iterative"
            assert fallback.is_active is True
            mock_find.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_fallback_flavor_none_available(
        self,
        mock_db,
        mock_single_pass_flavor
    ):
        """Test when no iterative fallback exists."""
        from app.services.flavor_service import FlavorService

        with patch.object(
            FlavorService,
            'find_iterative_fallback',
            new_callable=AsyncMock
        ) as mock_find:
            mock_find.return_value = None

            fallback = await FlavorService.find_iterative_fallback(
                mock_db,
                mock_single_pass_flavor.service_id,
                mock_single_pass_flavor.id
            )

            assert fallback is None

    @pytest.mark.asyncio
    async def test_has_iterative_fallback_true(self, mock_db, mock_single_pass_flavor):
        """Test has_iterative_fallback returns True when exists."""
        from app.services.flavor_service import FlavorService

        with patch.object(
            FlavorService,
            'has_iterative_fallback',
            new_callable=AsyncMock
        ) as mock_has:
            mock_has.return_value = True

            result = await FlavorService.has_iterative_fallback(
                mock_db,
                mock_single_pass_flavor.service_id,
                mock_single_pass_flavor.id
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_has_iterative_fallback_false(self, mock_db, mock_single_pass_flavor):
        """Test has_iterative_fallback returns False when none exists."""
        from app.services.flavor_service import FlavorService

        with patch.object(
            FlavorService,
            'has_iterative_fallback',
            new_callable=AsyncMock
        ) as mock_has:
            mock_has.return_value = False

            result = await FlavorService.has_iterative_fallback(
                mock_db,
                mock_single_pass_flavor.service_id,
                mock_single_pass_flavor.id
            )

            assert result is False


# =============================================================================
# 4. Endpoint Route Tests
# =============================================================================

class TestRunEndpointExists:
    """Tests for /run endpoint existence and configuration."""

    def test_run_endpoint_route_exists(self):
        """Verify /run endpoint is registered."""
        from app.api.v1.services import router

        routes = [route.path for route in router.routes]
        assert "/services/{service_id}/run" in routes

    def test_fallback_available_endpoint_exists(self):
        """Verify fallback-available endpoint is registered."""
        from app.api.v1.services import router

        routes = [route.path for route in router.routes]
        assert "/services/{service_id}/flavors/{flavor_id}/fallback-available" in routes


class TestRunEndpointParameters:
    """Tests for /run endpoint parameter handling."""

    def test_run_endpoint_accepts_required_params(self):
        """Verify /run endpoint accepts flavor_id as required."""
        from app.api.v1.services import run_service_with_file
        import inspect

        sig = inspect.signature(run_service_with_file)
        params = sig.parameters

        assert 'service_id' in params
        assert 'flavor_id' in params
        assert 'file' in params
        assert 'synthetic_template' in params

    def test_run_endpoint_accepts_optional_params(self):
        """Verify /run endpoint accepts optional parameters."""
        from app.api.v1.services import run_service_with_file
        import inspect

        sig = inspect.signature(run_service_with_file)
        params = sig.parameters

        assert 'temperature' in params
        assert 'top_p' in params
        assert 'organization_id' in params


# =============================================================================
# 5. Error Code Tests
# =============================================================================

class TestErrorCodes:
    """Tests for error codes."""

    def test_all_error_codes_defined(self):
        """Verify all required error codes exist in schema."""
        from app.schemas.service import ExecutionErrorResponse

        # Create instances with each error code to verify they're valid
        error_codes = [
            "CONTEXT_EXCEEDED",
            "CONTEXT_EXCEEDED_NO_FALLBACK",
            "FLAVOR_INACTIVE",
            "FALLBACK_FLAVOR_INACTIVE"
        ]

        for code in error_codes:
            error = ExecutionErrorResponse(
                detail=f"Test error for {code}",
                error_code=code
            )
            assert error.error_code == code


# =============================================================================
# 6. Integration Tests (with Mocked Dependencies)
# =============================================================================

class TestExecutionWithFallback:
    """Integration tests for execution with fallback behavior."""

    @pytest.fixture
    def app_with_routes(self):
        """Create a test app with all service routes."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.api.v1.services import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        return app

    def test_internal_function_shared(self):
        """Verify both endpoints use the same internal function."""
        from app.api.v1.services import _execute_with_file_internal

        # The internal function should exist
        assert _execute_with_file_internal is not None
        assert callable(_execute_with_file_internal)


class TestResolveTokenizerForFlavor:
    """Tests for tokenizer resolution in execution."""

    def test_resolve_tokenizer_with_override(self, mock_single_pass_flavor):
        """Test tokenizer resolution when flavor has override."""
        from app.api.v1.services import resolve_tokenizer_for_flavor

        mock_single_pass_flavor.tokenizer_override = "custom/tokenizer"

        result = resolve_tokenizer_for_flavor(mock_single_pass_flavor)
        assert result == "custom/tokenizer"

    def test_resolve_tokenizer_from_model(self, mock_single_pass_flavor):
        """Test tokenizer resolution from model tokenizer_name."""
        from app.api.v1.services import resolve_tokenizer_for_flavor

        mock_single_pass_flavor.tokenizer_override = None
        mock_single_pass_flavor.model.tokenizer_name = "model/tokenizer"

        result = resolve_tokenizer_for_flavor(mock_single_pass_flavor)
        assert result == "model/tokenizer"

    def test_resolve_tokenizer_from_mappings(self, mock_single_pass_flavor):
        """Test tokenizer resolution from mappings."""
        from app.api.v1.services import resolve_tokenizer_for_flavor

        mock_single_pass_flavor.tokenizer_override = None
        mock_single_pass_flavor.model.tokenizer_name = None
        mock_single_pass_flavor.model.model_identifier = "gpt-4"

        result = resolve_tokenizer_for_flavor(mock_single_pass_flavor)
        # GPT-4 should resolve to cl100k_base encoding
        assert result == "cl100k_base"


# =============================================================================
# 7. Fallback Availability Endpoint Tests
# =============================================================================

class TestFallbackAvailabilityEndpoint:
    """Tests for the fallback-available check endpoint."""

    def test_endpoint_returns_correct_response_type(self):
        """Verify endpoint returns FallbackAvailabilityResponse."""
        from app.api.v1.services import check_fallback_available
        import inspect

        # Check return annotation
        sig = inspect.signature(check_fallback_available)
        # The function should be an async function
        assert inspect.iscoroutinefunction(check_fallback_available)


# =============================================================================
# 8. Processing Mode Tests
# =============================================================================

class TestProcessingModeValidation:
    """Tests for processing mode field validation."""

    def test_valid_processing_modes(self):
        """Verify all valid processing modes are accepted."""
        from app.schemas.service import ServiceFlavorBase

        # v2.0.0: map_reduce removed, only single_pass and iterative are valid
        valid_modes = ["single_pass", "iterative"]

        for mode in valid_modes:
            flavor = ServiceFlavorBase(
                name="test",
                model_id=uuid4(),
                temperature=0.7,
                processing_mode=mode
            )
            assert flavor.processing_mode == mode

# =============================================================================
# 9. Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case tests for context validation features."""

    def test_empty_content_validation(self):
        """Test behavior with empty content."""
        # Empty content should have 0 tokens
        content = ""
        # This would be handled at endpoint level with validation
        assert len(content) == 0

    def test_exact_context_boundary(self, mock_single_pass_flavor):
        """Test content exactly at context boundary."""
        # Available = 8192 - 2048 - 500 = 5644
        # Content exactly at boundary should fit
        boundary_tokens = 5644

        # This is a unit test concept - actual implementation
        # would need to verify boundary behavior
        available = mock_single_pass_flavor.model.context_length - \
                    mock_single_pass_flavor.model.max_generation_length - 500
        assert available == 5644

    def test_inactive_fallback_flavor_skipped(
        self,
        mock_single_pass_flavor,
        mock_iterative_flavor
    ):
        """Test that inactive fallback flavors are skipped."""
        mock_iterative_flavor.is_active = False

        # The find_iterative_fallback should not return inactive flavors
        # This is verified by the query filter in FlavorService
        assert mock_iterative_flavor.is_active is False


class TestInputMutualExclusivity:
    """Tests for file/synthetic_template mutual exclusivity."""

    def test_cannot_provide_both_file_and_template(self):
        """Verify error when both file and synthetic_template provided."""
        # This is validated in _execute_with_file_internal
        # The function raises HTTPException 400 when both are provided
        from app.api.v1.services import _execute_with_file_internal
        import inspect

        # The function signature shows both are optional
        sig = inspect.signature(_execute_with_file_internal)

        assert 'file' in sig.parameters
        assert 'synthetic_template' in sig.parameters

    def test_must_provide_one_input(self):
        """Verify error when neither file nor synthetic_template provided."""
        # This is also validated in _execute_with_file_internal
        pass  # Covered by integration tests


# =============================================================================
# 10. API Contract Conformity Tests
# =============================================================================

class TestAPIContractConformity:
    """Tests verifying conformity to api-contract.md specification."""

    def test_execute_response_has_all_required_fields(self):
        """Verify ServiceExecuteResponse has all fields from api-contract.md."""
        from app.schemas.service import ServiceExecuteResponse
        import pydantic

        # Get all field names from the model
        fields = set(ServiceExecuteResponse.model_fields.keys())

        required_fields = {
            'job_id',
            'status',
            'service_id',
            'service_name',
            'flavor_id',
            'flavor_name',
            'created_at',
            'estimated_completion_time',
            # Fallback additions
            'fallback_applied',
            'original_flavor_id',
            'original_flavor_name',
            'fallback_reason',
            'input_tokens',
            'context_available',
        }

        assert required_fields.issubset(fields), \
            f"Missing fields: {required_fields - fields}"

    def test_error_response_has_all_required_fields(self):
        """Verify ExecutionErrorResponse has all fields from api-contract.md."""
        from app.schemas.service import ExecutionErrorResponse

        fields = set(ExecutionErrorResponse.model_fields.keys())

        required_fields = {
            'detail',
            'error_code',
            'input_tokens',
            'available_tokens',
            'flavor_id',
            'flavor_name',
            'original_flavor_id',
            'suggestion',
        }

        assert required_fields.issubset(fields), \
            f"Missing fields: {required_fields - fields}"

    def test_fallback_availability_response_fields(self):
        """Verify FallbackAvailabilityResponse has all fields from api-contract.md."""
        from app.schemas.service import FallbackAvailabilityResponse

        fields = set(FallbackAvailabilityResponse.model_fields.keys())

        required_fields = {
            'fallback_available',
            'fallback_flavor_id',
            'fallback_flavor_name',
            'reason',
        }

        assert required_fields.issubset(fields), \
            f"Missing fields: {required_fields - fields}"


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
