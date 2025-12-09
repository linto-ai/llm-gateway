#!/usr/bin/env python3
"""
Prompt Types and Service Types API Tests

Tests covering:
1. GET/POST/PATCH/DELETE /api/v1/prompt-types
2. GET/POST/PATCH/DELETE /api/v1/service-types
3. Prompts API prompt_type field (object, not string)
4. Prompt filtering by prompt_type code
5. System type protection (cannot delete system types)
"""

import pytest
import requests
import os
from uuid import uuid4

# API Base URL
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
API_V1_URL = f"{API_BASE_URL}/api/v1"


# =============================================================================
# Helper Functions
# =============================================================================

def get_json(path, params=None):
    """GET request helper."""
    response = requests.get(f"{API_V1_URL}{path}", params=params, timeout=30)
    return response.status_code, response.json() if response.content else None


def post_json(path, data):
    """POST request helper."""
    response = requests.post(f"{API_V1_URL}{path}", json=data, timeout=30)
    return response.status_code, response.json() if response.content else None


def patch_json(path, data):
    """PATCH request helper."""
    response = requests.patch(f"{API_V1_URL}{path}", json=data, timeout=30)
    return response.status_code, response.json() if response.content else None


def delete_resource(path):
    """DELETE request helper."""
    response = requests.delete(f"{API_V1_URL}{path}", timeout=30)
    return response.status_code


# =============================================================================
# Prompt Types API Tests
# =============================================================================

class TestPromptTypesListAPI:
    """Tests for GET /api/v1/prompt-types."""

    def test_list_prompt_types_returns_200(self):
        """GET /prompt-types returns 200 with list."""
        status, data = get_json("/prompt-types")
        assert status == 200, f"Expected 200, got {status}"
        assert isinstance(data, list), "Response should be a list"

    def test_list_prompt_types_has_system_types(self):
        """GET /prompt-types includes system types (standard, reduce)."""
        status, data = get_json("/prompt-types")
        assert status == 200

        codes = [pt["code"] for pt in data]
        assert "standard" in codes, "Missing system type 'standard'"
        assert "reduce" in codes, "Missing system type 'reduce'"

    def test_list_prompt_types_response_structure(self):
        """Verify prompt type response has all required fields."""
        status, data = get_json("/prompt-types")
        assert status == 200
        assert len(data) > 0, "Expected at least one prompt type"

        pt = data[0]
        required_fields = [
            "id", "code", "name", "description",
            "is_system", "is_active", "display_order",
            "created_at", "updated_at"
        ]
        for field in required_fields:
            assert field in pt, f"Missing required field: {field}"

    def test_list_prompt_types_name_i18n(self):
        """Verify name field has i18n structure (en, fr)."""
        status, data = get_json("/prompt-types")
        assert status == 200

        for pt in data:
            assert "name" in pt
            assert "en" in pt["name"], f"Missing 'en' in name for {pt['code']}"

    def test_list_prompt_types_active_only_filter(self):
        """GET /prompt-types?active_only=true filters inactive."""
        status, data = get_json("/prompt-types", {"active_only": "true"})
        assert status == 200

        for pt in data:
            assert pt["is_active"] is True, f"Found inactive type: {pt['code']}"


class TestPromptTypesCreateAPI:
    """Tests for POST /api/v1/prompt-types."""

    def test_create_prompt_type_success(self):
        """POST /prompt-types creates new type successfully."""
        code = f"qa_test_{uuid4().hex[:8]}"
        data = {
            "code": code,
            "name": {"en": "QA Test Type", "fr": "Type Test QA"},
            "description": {"en": "Test description"},
            "is_active": True,
            "display_order": 99
        }

        status, result = post_json("/prompt-types", data)

        try:
            assert status == 201, f"Expected 201, got {status}: {result}"
            assert result["code"] == code
            assert result["name"]["en"] == "QA Test Type"
            assert result["is_system"] is False, "New types should not be system"
            assert "id" in result
        finally:
            # Cleanup
            if status == 201:
                delete_resource(f"/prompt-types/{result['id']}")

    def test_create_prompt_type_duplicate_code_409(self):
        """POST /prompt-types with duplicate code returns 409."""
        data = {
            "code": "standard",  # Already exists as system type
            "name": {"en": "Duplicate Test"}
        }

        status, result = post_json("/prompt-types", data)
        assert status == 409, f"Expected 409 for duplicate code, got {status}"
        assert "already exists" in result.get("detail", "").lower()

    def test_create_prompt_type_invalid_code_pattern_422(self):
        """POST /prompt-types with invalid code pattern returns 422."""
        data = {
            "code": "INVALID_CAPS",  # Must be lowercase
            "name": {"en": "Test"}
        }

        status, result = post_json("/prompt-types", data)
        assert status == 422, f"Expected 422 for invalid code, got {status}"

    def test_create_prompt_type_missing_name_422(self):
        """POST /prompt-types without name returns 422."""
        data = {"code": "test_missing_name"}

        status, result = post_json("/prompt-types", data)
        assert status == 422, f"Expected 422 for missing name, got {status}"


class TestPromptTypesGetByIdAPI:
    """Tests for GET /api/v1/prompt-types/{id}."""

    def test_get_prompt_type_by_id_success(self):
        """GET /prompt-types/{id} returns the type."""
        # First get the list to find an ID
        status, data = get_json("/prompt-types")
        assert status == 200 and len(data) > 0

        pt_id = data[0]["id"]
        status, result = get_json(f"/prompt-types/{pt_id}")

        assert status == 200, f"Expected 200, got {status}"
        assert result["id"] == pt_id

    def test_get_prompt_type_not_found_404(self):
        """GET /prompt-types/{id} with unknown ID returns 404."""
        status, result = get_json("/prompt-types/00000000-0000-0000-0000-000000000000")
        assert status == 404, f"Expected 404, got {status}"


class TestPromptTypesUpdateAPI:
    """Tests for PATCH /api/v1/prompt-types/{id}."""

    def test_patch_prompt_type_success(self):
        """PATCH /prompt-types/{id} updates the type."""
        # Create a test type
        code = f"qa_patch_{uuid4().hex[:8]}"
        create_data = {
            "code": code,
            "name": {"en": "Original Name"},
            "display_order": 50
        }

        status, created = post_json("/prompt-types", create_data)
        assert status == 201

        try:
            # Update it
            update_data = {
                "name": {"en": "Updated Name", "fr": "Nom mis a jour"},
                "display_order": 60
            }
            status, result = patch_json(f"/prompt-types/{created['id']}", update_data)

            assert status == 200, f"Expected 200, got {status}"
            assert result["name"]["en"] == "Updated Name"
            assert result["display_order"] == 60
        finally:
            delete_resource(f"/prompt-types/{created['id']}")

    def test_patch_prompt_type_not_found_404(self):
        """PATCH /prompt-types/{id} with unknown ID returns 404."""
        status, result = patch_json(
            "/prompt-types/00000000-0000-0000-0000-000000000000",
            {"name": {"en": "Test"}}
        )
        assert status == 404


class TestPromptTypesDeleteAPI:
    """Tests for DELETE /api/v1/prompt-types/{id}."""

    def test_delete_prompt_type_non_system_success(self):
        """DELETE /prompt-types/{id} deletes non-system type."""
        # Create a test type
        code = f"qa_delete_{uuid4().hex[:8]}"
        create_data = {
            "code": code,
            "name": {"en": "Delete Test"}
        }

        status, created = post_json("/prompt-types", create_data)
        assert status == 201

        # Delete it
        status = delete_resource(f"/prompt-types/{created['id']}")
        assert status == 204, f"Expected 204, got {status}"

        # Verify it's gone
        status, _ = get_json(f"/prompt-types/{created['id']}")
        assert status == 404

    def test_delete_prompt_type_system_403(self):
        """DELETE /prompt-types/{id} for system type returns 403."""
        # Get the 'standard' system type ID
        status, data = get_json("/prompt-types")
        assert status == 200

        standard = next((pt for pt in data if pt["code"] == "standard"), None)
        assert standard is not None, "System type 'standard' not found"
        assert standard["is_system"] is True

        # Try to delete it
        status = delete_resource(f"/prompt-types/{standard['id']}")
        assert status == 403, f"Expected 403 for system type deletion, got {status}"

    def test_delete_prompt_type_not_found_404(self):
        """DELETE /prompt-types/{id} with unknown ID returns 404."""
        status = delete_resource("/prompt-types/00000000-0000-0000-0000-000000000000")
        assert status == 404


# =============================================================================
# Service Types API Tests
# =============================================================================

class TestServiceTypesListAPI:
    """Tests for GET /api/v1/service-types."""

    def test_list_service_types_returns_200(self):
        """GET /service-types returns 200 with list."""
        status, data = get_json("/service-types")
        assert status == 200, f"Expected 200, got {status}"
        assert isinstance(data, list), "Response should be a list"

    def test_list_service_types_has_system_types(self):
        """GET /service-types includes expected system types."""
        status, data = get_json("/service-types")
        assert status == 200

        codes = [st["code"] for st in data]
        expected = ["summary", "translation", "categorization"]
        for code in expected:
            assert code in codes, f"Missing system type '{code}'"

    def test_list_service_types_i18n_names(self):
        """Verify service type name has i18n structure."""
        status, data = get_json("/service-types")
        assert status == 200

        for st in data:
            assert "name" in st
            assert "en" in st["name"], f"Missing 'en' in name for {st['code']}"
            assert "fr" in st["name"], f"Missing 'fr' in name for {st['code']}"

    def test_list_service_types_response_structure(self):
        """Verify service type response has all required fields."""
        status, data = get_json("/service-types")
        assert status == 200
        assert len(data) > 0

        st = data[0]
        required_fields = [
            "id", "code", "name", "description",
            "is_system", "is_active", "display_order",
            "created_at", "updated_at"
        ]
        for field in required_fields:
            assert field in st, f"Missing required field: {field}"


class TestServiceTypesCreateAPI:
    """Tests for POST /api/v1/service-types."""

    def test_create_service_type_success(self):
        """POST /service-types creates new type."""
        code = f"qa_svc_{uuid4().hex[:8]}"
        data = {
            "code": code,
            "name": {"en": "QA Service", "fr": "Service QA"},
            "description": {"en": "Test service type"},
            "is_active": True,
            "display_order": 99
        }

        status, result = post_json("/service-types", data)

        try:
            assert status == 201, f"Expected 201, got {status}: {result}"
            assert result["code"] == code
            assert result["is_system"] is False
        finally:
            if status == 201:
                delete_resource(f"/service-types/{result['id']}")

    def test_create_service_type_duplicate_code_409(self):
        """POST /service-types with duplicate code returns 409."""
        data = {
            "code": "summary",  # Already exists
            "name": {"en": "Duplicate Test"}
        }

        status, result = post_json("/service-types", data)
        assert status == 409, f"Expected 409 for duplicate code, got {status}"


class TestServiceTypesDeleteAPI:
    """Tests for DELETE /api/v1/service-types/{id}."""

    def test_delete_service_type_system_403(self):
        """DELETE /service-types/{id} for system type returns 403."""
        status, data = get_json("/service-types")
        assert status == 200

        summary = next((st for st in data if st["code"] == "summary"), None)
        assert summary is not None and summary["is_system"] is True

        status = delete_resource(f"/service-types/{summary['id']}")
        assert status == 403, f"Expected 403 for system type deletion, got {status}"

    def test_delete_service_type_non_system_success(self):
        """DELETE /service-types/{id} deletes non-system type."""
        code = f"qa_del_svc_{uuid4().hex[:8]}"
        create_data = {
            "code": code,
            "name": {"en": "Delete Test"}
        }

        status, created = post_json("/service-types", create_data)
        assert status == 201

        status = delete_resource(f"/service-types/{created['id']}")
        assert status == 204


# =============================================================================
# Prompts API - prompt_type Object Tests
# =============================================================================

class TestPromptsPromptTypeObject:
    """Tests for prompts API prompt_type field (object, not string)."""

    def test_prompts_response_has_prompt_type_object(self):
        """GET /prompts returns prompt_type as object, not string."""
        status, data = get_json("/prompts", {"page_size": 5})
        assert status == 200

        items = data.get("items", [])
        if not items:
            pytest.skip("No prompts available")

        for prompt in items:
            if prompt.get("prompt_type") is not None:
                pt = prompt["prompt_type"]
                assert isinstance(pt, dict), (
                    f"prompt_type should be an object, got {type(pt)}"
                )
                assert "id" in pt, "prompt_type object should have 'id'"
                assert "code" in pt, "prompt_type object should have 'code'"
                assert "name" in pt, "prompt_type object should have 'name'"

    def test_prompts_filter_by_prompt_type_code(self):
        """GET /prompts?prompt_type=reduce filters correctly."""
        status, data = get_json("/prompts", {"prompt_type": "reduce"})
        assert status == 200

        items = data.get("items", [])
        for prompt in items:
            pt = prompt.get("prompt_type")
            assert pt is not None, "Filtered prompts should have prompt_type"
            assert pt["code"] == "reduce", f"Expected code='reduce', got '{pt['code']}'"

    def test_prompts_filter_by_prompt_type_standard(self):
        """GET /prompts?prompt_type=standard filters correctly."""
        status, data = get_json("/prompts", {"prompt_type": "standard"})
        assert status == 200

        items = data.get("items", [])
        for prompt in items:
            pt = prompt.get("prompt_type")
            if pt is not None:  # Some may have null
                assert pt["code"] == "standard"

    def test_templates_filter_by_prompt_type(self):
        """GET /prompts/templates?prompt_type=reduce filters correctly."""
        status, data = get_json("/prompts/templates", {"prompt_type": "reduce"})
        assert status == 200

        items = data.get("items", [])
        for template in items:
            pt = template.get("prompt_type")
            if pt is not None:
                assert pt["code"] == "reduce"


class TestPromptsPromptTypeResponseSchema:
    """Tests for prompt response schema compliance."""

    def test_prompt_type_object_has_i18n_name(self):
        """Verify prompt_type.name has i18n structure."""
        status, data = get_json("/prompts", {"page_size": 10})
        assert status == 200

        for prompt in data.get("items", []):
            pt = prompt.get("prompt_type")
            if pt is not None:
                assert "name" in pt
                assert "en" in pt["name"], "prompt_type.name should have 'en'"

    def test_prompt_type_object_fields(self):
        """Verify prompt_type object has all contract fields."""
        status, data = get_json("/prompts", {"prompt_type": "standard", "page_size": 1})
        assert status == 200

        items = data.get("items", [])
        if not items:
            pytest.skip("No standard prompts available")

        pt = items[0].get("prompt_type")
        if pt is None:
            pytest.skip("Prompt has null prompt_type")

        required_fields = [
            "id", "code", "name", "description",
            "is_system", "is_active", "display_order",
            "created_at", "updated_at"
        ]
        for field in required_fields:
            assert field in pt, f"prompt_type missing field: {field}"


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
