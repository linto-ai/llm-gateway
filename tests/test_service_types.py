#!/usr/bin/env python3
"""
Service Types Validation Tests

Tests covering:
1. GET /api/v1/service-types returns exactly 6 types (NO "document" or "extraction")
2. Valid types: summary, translation, categorization, diarization_correction, speaker_correction, generic
3. GET /api/v1/prompt-types?service_type=summary returns prompt types linked to summary
4. Prompts API works correctly

Note: "document" and "extraction" service types have been REMOVED.
Only 6 valid service types remain.
"""

import pytest
import requests
import os
from uuid import uuid4

# API Base URL
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
API_V1_URL = f"{API_BASE_URL}/api/v1"

# The EXACT 6 valid service types (extraction removed)
VALID_SERVICE_TYPES = {
    "summary",
    "translation",
    "categorization",
    "diarization_correction",
    "speaker_correction",
    "generic",
}

# The REMOVED service types
REMOVED_SERVICE_TYPES = {"document", "extraction"}


# =============================================================================
# Helper Functions
# =============================================================================

def get_json(path, params=None, timeout=30):
    """GET request helper."""
    response = requests.get(f"{API_V1_URL}{path}", params=params, timeout=timeout)
    return response.status_code, response.json() if response.content else None


def post_json(path, data, timeout=30):
    """POST request helper."""
    response = requests.post(f"{API_V1_URL}{path}", json=data, timeout=timeout)
    return response.status_code, response.json() if response.content else None


def patch_json(path, data, timeout=30):
    """PATCH request helper."""
    response = requests.patch(f"{API_V1_URL}{path}", json=data, timeout=timeout)
    return response.status_code, response.json() if response.content else None


def delete_resource(path, timeout=30):
    """DELETE request helper."""
    response = requests.delete(f"{API_V1_URL}{path}", timeout=timeout)
    return response.status_code


def cleanup_prompt(prompt_id):
    """Delete a prompt by ID (for cleanup)."""
    try:
        delete_resource(f"/prompts/{prompt_id}")
    except Exception:
        pass


# =============================================================================
# 1. Service Types - Core Validation
# =============================================================================

class TestServiceTypesCount:
    """Verify exactly 6 service types exist (NO document or extraction)."""

    def test_service_types_returns_exactly_6_types(self):
        """
        GET /service-types returns EXACTLY 6 types.

        Valid types:
        - summary, translation, categorization, diarization_correction,
          speaker_correction, generic
        - NO "document" or "extraction" types
        """
        status, data = get_json("/service-types")

        assert status == 200, f"Expected 200, got {status}"
        assert isinstance(data, list), "Response should be a list"

        codes = {st["code"] for st in data}

        # Count check: EXACTLY 6 types
        assert len(data) == 6, (
            f"Expected EXACTLY 6 service types, got {len(data)}. "
            f"Types found: {codes}"
        )

    def test_service_types_no_removed_types(self):
        """
        GET /service-types does NOT include removed types.

        Note: "document" and "extraction" service types have been REMOVED.
        """
        status, data = get_json("/service-types")

        assert status == 200
        codes = {st["code"] for st in data}

        for removed_type in REMOVED_SERVICE_TYPES:
            assert removed_type not in codes, (
                f"FAILURE: Found '{removed_type}' in service types. "
                f"This type should have been REMOVED. "
                f"All codes found: {codes}"
            )

    def test_service_types_has_all_valid_types(self):
        """
        GET /service-types includes ALL 6 valid types.

        Valid types:
        - summary, translation, categorization, diarization_correction,
          speaker_correction, generic
        """
        status, data = get_json("/service-types")

        assert status == 200
        codes = {st["code"] for st in data}

        missing = VALID_SERVICE_TYPES - codes
        extra = codes - VALID_SERVICE_TYPES

        assert missing == set(), (
            f"Missing expected service types: {missing}"
        )
        assert extra == set(), (
            f"Found unexpected service types: {extra}"
        )

    @pytest.mark.parametrize("expected_type", list(VALID_SERVICE_TYPES))
    def test_each_valid_service_type_exists(self, expected_type):
        """Verify each valid service type is present in the API response."""
        status, data = get_json("/service-types")

        assert status == 200
        codes = {st["code"] for st in data}

        assert expected_type in codes, (
            f"Service type '{expected_type}' not found in API response. "
            f"Available types: {codes}"
        )


# =============================================================================
# 2. Service Types - Response Structure
# =============================================================================

class TestServiceTypesResponseStructure:
    """Tests for service type response structure compliance."""

    def test_service_type_response_has_required_fields(self):
        """Verify each service type has all required fields."""
        status, data = get_json("/service-types")

        assert status == 200
        assert len(data) > 0

        required_fields = [
            "id",
            "code",
            "name",
            "description",
            "is_system",
            "is_active",
            "display_order",
            "created_at",
            "updated_at",
        ]

        for st in data:
            for field in required_fields:
                assert field in st, (
                    f"Service type '{st.get('code', 'unknown')}' missing field: {field}"
                )

    def test_service_type_i18n_names(self):
        """Verify service type names have i18n structure (en, fr)."""
        status, data = get_json("/service-types")

        assert status == 200

        for st in data:
            assert "name" in st
            assert isinstance(st["name"], dict), (
                f"Service type '{st['code']}' name should be dict, got {type(st['name'])}"
            )
            assert "en" in st["name"], (
                f"Service type '{st['code']}' missing English name"
            )
            assert "fr" in st["name"], (
                f"Service type '{st['code']}' missing French name"
            )

    def test_all_service_types_are_system_and_active(self):
        """Verify all 7 core service types are system types and active."""
        status, data = get_json("/service-types")

        assert status == 200

        for st in data:
            if st["code"] in VALID_SERVICE_TYPES:
                assert st["is_system"] is True, (
                    f"Service type '{st['code']}' should be a system type"
                )
                assert st["is_active"] is True, (
                    f"Service type '{st['code']}' should be active"
                )


# =============================================================================
# 3. Prompt Types - Service Type Filter
# =============================================================================

class TestPromptTypesServiceTypeFilter:
    """Tests for GET /api/v1/prompt-types?service_type=summary."""

    def test_prompt_types_filter_by_service_type_summary(self):
        """
        GET /prompt-types?service_type=summary returns prompt types linked to summary.

        Prompt types can be filtered by service_type.
        """
        status, data = get_json("/prompt-types", {"service_type": "summary"})

        assert status == 200, f"Expected 200, got {status}: {data}"
        assert isinstance(data, list), "Response should be a list"

        # Should return prompt types (may be 0 or more, but request should succeed)
        # If there are results, verify they are correctly linked
        for pt in data:
            # The prompt type should be linked to a service_type
            # Check if service_type field exists and is relevant
            if pt.get("service_type"):
                assert pt["service_type"].get("code") == "summary", (
                    f"Prompt type '{pt['code']}' filtered for summary but has "
                    f"service_type '{pt['service_type'].get('code')}'"
                )

    def test_prompt_types_without_filter_returns_all(self):
        """GET /prompt-types without filter returns all prompt types."""
        status, data = get_json("/prompt-types")

        assert status == 200
        assert isinstance(data, list)

        # Should have at least 'standard' and 'reduce' system types
        codes = [pt["code"] for pt in data]
        assert "standard" in codes, "Missing system type 'standard'"
        assert "reduce" in codes, "Missing system type 'reduce'"

    def test_prompt_types_response_structure(self):
        """Verify prompt type response has all required fields."""
        status, data = get_json("/prompt-types")

        assert status == 200
        assert len(data) > 0

        required_fields = [
            "id",
            "code",
            "name",
            "description",
            "is_system",
            "is_active",
            "display_order",
            "created_at",
            "updated_at",
        ]

        for pt in data:
            for field in required_fields:
                assert field in pt, (
                    f"Prompt type '{pt.get('code', 'unknown')}' missing field: {field}"
                )


# =============================================================================
# 4. Prompts API - Works with Valid Service Types
# =============================================================================

class TestPromptsAPIWithServiceTypes:
    """Tests for Prompts API using valid service types."""

    def test_create_prompt_with_valid_service_type(self):
        """Create prompt with a valid service type succeeds."""
        prompt_data = {
            "name": f"qa_test_summary_{uuid4().hex[:8]}",
            "content": "Test prompt content",
            "language": "en",
            "service_type": "summary",
            "prompt_category": "user",
            "prompt_role": "main",
        }

        status, data = post_json("/prompts", prompt_data)

        try:
            assert status == 201, f"Expected 201, got {status}: {data}"
            assert data["service_type"] == "summary"
            assert data["prompt_category"] == "user"
        finally:
            if status == 201 and data:
                cleanup_prompt(data["id"])

    def test_create_prompt_with_document_type_fails(self):
        """
        Create prompt with 'document' service type FAILS.

        Note: 'document' type has been removed from the database.
        API returns 400 (Bad Request) when service type is not found.
        """
        prompt_data = {
            "name": f"qa_test_document_{uuid4().hex[:8]}",
            "content": "This should fail - document type removed",
            "language": "en",
            "service_type": "document",  # REMOVED type
            "prompt_category": "user",
        }

        status, data = post_json("/prompts", prompt_data)

        # API returns 400 when service_type is not found in database
        assert status == 400, (
            f"Expected 400 for removed 'document' service type, got {status}: {data}"
        )
        # Should mention service type not found
        assert "not found" in data.get("detail", "").lower(), (
            f"Expected error about service type not found, got: {data}"
        )

    @pytest.mark.parametrize("service_type", list(VALID_SERVICE_TYPES))
    def test_create_prompt_with_each_valid_service_type(self, service_type):
        """Create prompt with each valid service type succeeds."""
        prompt_data = {
            "name": f"qa_test_{service_type}_{uuid4().hex[:8]}",
            "content": f"Test prompt for {service_type}",
            "language": "en",
            "service_type": service_type,
            "prompt_category": "user",
            "prompt_role": "main",
        }

        status, data = post_json("/prompts", prompt_data)

        try:
            assert status == 201, (
                f"Expected 201 for service_type='{service_type}', got {status}: {data}"
            )
            assert data["service_type"] == service_type
        finally:
            if status == 201 and data:
                cleanup_prompt(data["id"])

    def test_list_prompts_filter_by_valid_service_type(self):
        """List prompts filtered by valid service type works."""
        status, data = get_json("/prompts", {"service_type": "summary"})

        assert status == 200, f"Expected 200, got {status}: {data}"
        assert "items" in data
        assert "total" in data

        # All returned prompts should have service_type='summary'
        for prompt in data["items"]:
            assert prompt.get("service_type") == "summary", (
                f"Prompt {prompt['id']} has service_type={prompt.get('service_type')}, "
                f"expected 'summary'"
            )

    def test_list_prompts_filter_by_removed_type_returns_empty(self):
        """List prompts filtered by 'document' returns empty (type removed)."""
        status, data = get_json("/prompts", {"service_type": "document"})

        # Should return 200 with empty results (no prompts with 'document' type)
        assert status == 200, f"Expected 200, got {status}"
        assert data["total"] == 0, (
            f"Expected 0 prompts with 'document' type (removed), got {data['total']}"
        )


# =============================================================================
# 5. Service Types - Document Type Should Not Exist
# =============================================================================

class TestDocumentTypeNotExists:
    """Tests to verify 'document' type does not exist in the system."""

    def test_document_service_type_not_in_list(self):
        """
        GET /service-types does NOT include 'document'.

        Note: The service-types API allows creating custom types, but
        after migration, 'document' should not exist.
        """
        status, data = get_json("/service-types")

        assert status == 200
        codes = {st["code"] for st in data}

        # After migration, 'document' should not be in the list
        assert "document" not in codes, (
            f"FAILURE: 'document' service type found in API response. "
            f"This type should have been removed by migration 004. "
            f"Types found: {codes}"
        )

    def test_prompts_cannot_use_document_type(self):
        """
        Prompts API rejects 'document' as service_type.

        The prompt service validates service_type against database lookup.
        Since 'document' was removed, it should be rejected.
        """
        prompt_data = {
            "name": f"qa_test_document_{uuid4().hex[:8]}",
            "content": "Test content",
            "language": "en",
            "service_type": "document",
            "prompt_category": "user",
        }

        status, data = post_json("/prompts", prompt_data)

        # Should fail because 'document' is not in service_types table
        assert status == 400, (
            f"Expected 400 for 'document' service type, got {status}: {data}"
        )


# =============================================================================
# 6. Integration - Service Creation Schema
# =============================================================================

class TestServiceCreationSchema:
    """Tests for service creation schema."""

    def test_service_creation_accepts_valid_types(self):
        """Verify the service schema accepts valid service types."""
        from app.schemas.service import ServiceCreate

        # This should not raise validation errors
        for service_type in VALID_SERVICE_TYPES:
            service = ServiceCreate(
                name=f"test-{service_type}",
                route=f"test-{service_type}-route",
                service_type=service_type,
                description={"en": "Test", "fr": "Test"},
            )
            assert service.service_type == service_type

    def test_service_schema_accepts_any_string_for_service_type(self):
        """
        Service schema accepts any string for service_type.

        Validation of service_type against valid types happens at the
        service layer (database lookup), not at schema level.
        """
        from app.schemas.service import ServiceCreate

        # Schema accepts any string, validation happens later
        service = ServiceCreate(
            name="test-any-type",
            route="test-any-route",
            service_type="any_custom_type",  # Any string accepted at schema level
            description={"en": "Test", "fr": "Test"},
        )
        assert service.service_type == "any_custom_type"


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
