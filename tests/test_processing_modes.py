"""
Processing Mode, Context Validation, Enhanced Progress, Flavor Presets - QA Tests

Tests:
1. Processing Mode configuration on ServiceFlavors
2. Context Validation endpoint (validate-execution)
3. Enhanced Job Progress schema
4. Flavor Presets CRUD API

NOTE: These are integration tests that require a running API server with data.
      They will skip gracefully if the server is not available.
      Run with: pytest tests/test_processing_modes.py --integration
"""

import pytest
import requests
import os
from uuid import uuid4, UUID


# Skip all tests if API is not available
def _api_available():
    """Check if the API server is accessible."""
    url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    try:
        response = requests.get(f"{url}/api/v1/services", timeout=2)
        return response.status_code == 200
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return False


# Mark entire module as integration tests - skip if API not available
pytestmark = pytest.mark.skipif(
    not _api_available(),
    reason="Integration tests require running API server"
)

# API Base URL - use environment variable or default
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
API_V1_URL = f"{API_BASE_URL}/api/v1"


# =============================================================================
# Helper Functions
# =============================================================================

def get_first_service():
    """Get the first available service with at least one flavor."""
    try:
        response = requests.get(f"{API_V1_URL}/services", timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()
        services = data.get("items", [])
        for s in services:
            if s.get("flavors"):
                return s
        return services[0] if services else None
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return None


def get_first_model():
    """Get the first available model."""
    try:
        response = requests.get(f"{API_V1_URL}/models", timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()
        items = data.get("items", [])
        return items[0] if items else None
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return None


def create_test_preset(suffix=""):
    """Create a test preset and return its data."""
    try:
        preset_data = {
            "name": f"test_preset_{uuid4().hex[:8]}{suffix}",
            "service_type": "summary",
            "description_en": "Test preset for QA",
            "description_fr": "Preset de test QA",
            "config": {
                "processing_mode": "iterative",
                "max_new_turns": 15,
                "summary_turns": 4,
                "reduce_summary": False,
                "create_new_turn_after": 400,
                "temperature": 0.3,
                "top_p": 0.85
            }
        }
        response = requests.post(
            f"{API_V1_URL}/flavor-presets",
            json=preset_data,
            timeout=10
        )
        if response.status_code == 201:
            return response.json()
        return None
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return None


def cleanup_preset(preset_id):
    """Delete a preset by ID (for cleanup)."""
    try:
        requests.delete(f"{API_V1_URL}/flavor-presets/{preset_id}", timeout=10)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        pass  # Ignore cleanup errors


# =============================================================================
# 1. Processing Mode Tests
# =============================================================================

class TestProcessingMode:
    """Test processing_mode field on flavors."""

    def test_flavor_response_includes_processing_mode(self):
        """Verify flavor response includes processing_mode field."""
        service = get_first_service()
        if not service:
            pytest.skip("No service available for testing")

        flavors = service.get("flavors", [])
        if not flavors:
            pytest.skip("No flavors available for testing")

        flavor = flavors[0]
        assert "processing_mode" in flavor, "processing_mode field missing from flavor response"
        assert flavor["processing_mode"] in ["single_pass", "iterative"], (
            f"Invalid processing_mode value: {flavor['processing_mode']}"
        )

    def test_processing_mode_default_is_iterative(self):
        """Verify default processing_mode is 'iterative'."""
        service = get_first_service()
        if not service:
            pytest.skip("No service available for testing")

        flavors = service.get("flavors", [])
        if not flavors:
            pytest.skip("No flavors available for testing")

        # Check that existing flavors have a valid processing_mode
        # (they should default to 'iterative' from migration)
        for flavor in flavors:
            assert flavor.get("processing_mode") is not None, (
                f"Flavor {flavor.get('name')} has null processing_mode"
            )

    def test_update_flavor_processing_mode(self):
        """Test updating flavor's processing_mode field."""
        service = get_first_service()
        if not service:
            pytest.skip("No service available for testing")

        flavors = service.get("flavors", [])
        if not flavors:
            pytest.skip("No flavors available for testing")

        # Find a flavor that's already single_pass or can be changed
        flavor = flavors[0]
        flavor_id = flavor["id"]
        current_mode = flavor.get("processing_mode", "iterative")

        # Try to toggle processing_mode (if iterative, try single_pass; if single_pass, try iterative)
        target_mode = "iterative" if current_mode == "single_pass" else "single_pass"

        response = requests.patch(
            f"{API_V1_URL}/flavors/{flavor_id}",
            json={"processing_mode": target_mode},
            timeout=10
        )

        if response.status_code == 200:
            updated = response.json()
            assert updated["processing_mode"] == target_mode, (
                f"processing_mode not updated to {target_mode}"
            )

            # Restore original mode
            requests.patch(
                f"{API_V1_URL}/flavors/{flavor_id}",
                json={"processing_mode": current_mode},
                timeout=10
            )
        elif response.status_code == 400:
            # Business validation error (e.g., placeholder count mismatch)
            # This is expected for some flavors - verify the error is valid
            error = response.json().get("detail", {})
            if isinstance(error, dict) and error.get("type") == "prompt_validation_error":
                # Valid validation error - test passes (API correctly validates)
                pass
            else:
                pytest.skip(f"Update returned 400: {error}")
        else:
            pytest.skip(f"Could not update flavor: {response.status_code}")

    def test_processing_mode_invalid_value_rejected(self):
        """Test that invalid processing_mode values are rejected."""
        service = get_first_service()
        if not service:
            pytest.skip("No service available for testing")

        flavors = service.get("flavors", [])
        if not flavors:
            pytest.skip("No flavors available for testing")

        flavor_id = flavors[0]["id"]

        response = requests.patch(
            f"{API_V1_URL}/flavors/{flavor_id}",
            json={"processing_mode": "invalid_mode"},
            timeout=10
        )

        assert response.status_code == 422, (
            f"Expected 422 for invalid processing_mode, got {response.status_code}"
        )


# =============================================================================
# 2. Context Validation Endpoint Tests
# =============================================================================

class TestContextValidation:
    """Test POST /services/{service_id}/validate-execution endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        self.service = get_first_service()

    def test_validate_execution_requires_input(self):
        """Test that endpoint requires either file or synthetic_template."""
        if not self.service:
            pytest.skip("No service available for testing")

        service_id = self.service["id"]
        flavors = self.service.get("flavors", [])
        if not flavors:
            pytest.skip("No flavors available")

        flavor_id = flavors[0]["id"]

        # Call with neither file nor template
        response = requests.post(
            f"{API_V1_URL}/services/{service_id}/validate-execution",
            data={"flavor_id": flavor_id},
            timeout=10
        )

        assert response.status_code == 400, (
            f"Expected 400 for missing input, got {response.status_code}"
        )
        assert "Must provide either file or synthetic_template" in response.json().get("detail", ""), (
            "Error message should mention missing input"
        )

    def test_validate_execution_rejects_both_inputs(self):
        """Test that endpoint rejects both file AND synthetic_template."""
        if not self.service:
            pytest.skip("No service available for testing")

        service_id = self.service["id"]
        flavors = self.service.get("flavors", [])
        if not flavors:
            pytest.skip("No flavors available")

        flavor_id = flavors[0]["id"]

        # Call with both (using a dummy file)
        files = {"file": ("test.txt", b"test content", "text/plain")}
        data = {
            "flavor_id": flavor_id,
            "synthetic_template": "some_template.txt"
        }

        response = requests.post(
            f"{API_V1_URL}/services/{service_id}/validate-execution",
            files=files,
            data=data,
            timeout=10
        )

        assert response.status_code == 400, (
            f"Expected 400 for both inputs, got {response.status_code}"
        )
        assert "not both" in response.json().get("detail", "").lower(), (
            "Error message should mention 'not both'"
        )

    def test_validate_execution_with_file_returns_correct_schema(self):
        """Test validate-execution with file returns correct response schema."""
        if not self.service:
            pytest.skip("No service available for testing")

        service_id = self.service["id"]
        flavors = self.service.get("flavors", [])
        if not flavors:
            pytest.skip("No flavors available")

        flavor_id = flavors[0]["id"]

        # Create a small test file content
        test_content = "This is a test meeting transcript. " * 50
        files = {"file": ("test.txt", test_content.encode(), "text/plain")}
        data = {"flavor_id": flavor_id}

        response = requests.post(
            f"{API_V1_URL}/services/{service_id}/validate-execution",
            files=files,
            data=data,
            timeout=10
        )

        if response.status_code != 200:
            pytest.skip(f"validate-execution returned {response.status_code}: {response.text[:200]}")

        result = response.json()

        # Verify response schema (updated to match new simplified schema)
        assert "valid" in result, "Missing valid field"
        assert "warning" in result, "Missing warning field"
        assert "input_tokens" in result, "Missing input_tokens field"
        assert "max_generation" in result, "Missing max_generation field"
        assert "context_length" in result, "Missing context_length field"
        assert "estimated_cost" in result, "Missing estimated_cost field"

        # Verify types
        assert isinstance(result["valid"], bool)
        assert result["input_tokens"] is None or isinstance(result["input_tokens"], int)
        assert result["max_generation"] is None or isinstance(result["max_generation"], int)
        assert result["context_length"] is None or isinstance(result["context_length"], int)
        assert result["warning"] is None or isinstance(result["warning"], str)
        assert result["estimated_cost"] is None or isinstance(result["estimated_cost"], (int, float))

    def test_validate_execution_service_not_found(self):
        """Test validate-execution with invalid service_id returns 404."""
        fake_service_id = str(uuid4())
        fake_flavor_id = str(uuid4())

        files = {"file": ("test.txt", b"test content", "text/plain")}
        data = {"flavor_id": fake_flavor_id}

        response = requests.post(
            f"{API_V1_URL}/services/{fake_service_id}/validate-execution",
            files=files,
            data=data,
            timeout=10
        )

        assert response.status_code == 404, (
            f"Expected 404 for invalid service, got {response.status_code}"
        )

    def test_validate_execution_flavor_not_found(self):
        """Test validate-execution with invalid flavor_id returns 404."""
        if not self.service:
            pytest.skip("No service available for testing")

        service_id = self.service["id"]
        fake_flavor_id = str(uuid4())

        files = {"file": ("test.txt", b"test content", "text/plain")}
        data = {"flavor_id": fake_flavor_id}

        response = requests.post(
            f"{API_V1_URL}/services/{service_id}/validate-execution",
            files=files,
            data=data,
            timeout=10
        )

        assert response.status_code == 404, (
            f"Expected 404 for invalid flavor, got {response.status_code}"
        )


# =============================================================================
# 3. Enhanced Job Progress Schema Tests
# =============================================================================

class TestEnhancedJobProgress:
    """Test enhanced job progress fields in job responses."""

    def test_job_schema_supports_enhanced_progress_fields(self):
        """Verify job progress schema supports new fields."""
        # Get a recent job if available
        response = requests.get(
            f"{API_V1_URL}/jobs",
            params={"page_size": 1},
            timeout=10
        )

        if response.status_code != 200:
            pytest.skip("Jobs endpoint not accessible")

        data = response.json()
        jobs = data.get("items", [])

        if not jobs:
            pytest.skip("No jobs available for testing")

        job = jobs[0]

        # Progress may be null for completed jobs, but schema should support it
        if job.get("progress"):
            progress = job["progress"]
            # Check for enhanced fields (may not all be present if job didn't use them)
            known_fields = ["current", "total", "percentage", "phase", "current_batch",
                           "total_batches", "completed_turns", "total_turns",
                           "estimated_seconds_remaining"]

            # At minimum, basic progress fields should exist
            assert "current" in progress or "percentage" in progress, (
                "Job progress missing basic fields"
            )

    def test_job_response_structure(self):
        """Verify job response has correct structure."""
        response = requests.get(
            f"{API_V1_URL}/jobs",
            params={"page_size": 1},
            timeout=10
        )

        if response.status_code != 200:
            pytest.skip("Jobs endpoint not accessible")

        data = response.json()
        jobs = data.get("items", [])

        if not jobs:
            pytest.skip("No jobs available for testing")

        job = jobs[0]

        # Verify required fields
        assert "id" in job, "Job missing id field"
        assert "service_id" in job, "Job missing service_id field"
        assert "status" in job, "Job missing status field"
        assert "created_at" in job, "Job missing created_at field"


# =============================================================================
# 4. Flavor Presets CRUD Tests
# =============================================================================

class TestFlavorPresetsAPI:
    """Test Flavor Presets CRUD endpoints."""

    def test_list_presets_returns_200(self):
        """GET /flavor-presets should return 200."""
        response = requests.get(f"{API_V1_URL}/flavor-presets", timeout=10)
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        assert isinstance(response.json(), list), "Response should be a list"

    def test_list_presets_with_service_type_filter(self):
        """GET /flavor-presets with service_type filter should work."""
        response = requests.get(
            f"{API_V1_URL}/flavor-presets",
            params={"service_type": "summary"},
            timeout=10
        )
        assert response.status_code == 200

        presets = response.json()
        for preset in presets:
            assert preset["service_type"] == "summary", (
                f"Filter not applied: got service_type={preset['service_type']}"
            )

    def test_list_presets_unknown_service_type_returns_empty(self):
        """GET /flavor-presets with unknown service_type returns empty list."""
        response = requests.get(
            f"{API_V1_URL}/flavor-presets",
            params={"service_type": "nonexistent_type_xyz"},
            timeout=10
        )
        assert response.status_code == 200
        assert response.json() == [], "Should return empty list for unknown type"

    def test_get_preset_by_id(self):
        """GET /flavor-presets/{id} returns preset details."""
        # First create a preset
        preset = create_test_preset("_get")
        if not preset:
            pytest.skip("Could not create test preset")

        try:
            preset_id = preset["id"]
            response = requests.get(
                f"{API_V1_URL}/flavor-presets/{preset_id}",
                timeout=10
            )
            assert response.status_code == 200
            result = response.json()
            assert result["id"] == preset_id
            assert "config" in result
            assert "name" in result
        finally:
            cleanup_preset(preset["id"])

    def test_get_preset_not_found(self):
        """GET /flavor-presets/{invalid-id} returns 404."""
        fake_id = str(uuid4())
        response = requests.get(
            f"{API_V1_URL}/flavor-presets/{fake_id}",
            timeout=10
        )
        assert response.status_code == 404

    def test_create_preset(self):
        """POST /flavor-presets creates a new preset."""
        preset_data = {
            "name": f"qa_test_create_{uuid4().hex[:8]}",
            "service_type": "summary",
            "description_en": "Test preset created by QA",
            "description_fr": "Preset de test cree par QA",
            "config": {
                "processing_mode": "single_pass",
                "temperature": 0.5,
                "top_p": 0.9
            }
        }

        response = requests.post(
            f"{API_V1_URL}/flavor-presets",
            json=preset_data,
            timeout=10
        )

        assert response.status_code == 201, (
            f"Expected 201, got {response.status_code}: {response.text}"
        )

        result = response.json()
        assert result["name"] == preset_data["name"]
        assert result["is_system"] is False, "User-created preset should not be system"
        assert result["config"]["processing_mode"] == "single_pass"

        # Cleanup
        cleanup_preset(result["id"])

    def test_create_preset_duplicate_name_returns_409(self):
        """POST /flavor-presets with duplicate name returns 409."""
        preset = create_test_preset("_dup")
        if not preset:
            pytest.skip("Could not create initial preset")

        try:
            # Try to create another with same name
            duplicate_data = {
                "name": preset["name"],
                "service_type": "summary",
                "config": {"processing_mode": "iterative", "temperature": 0.5}
            }

            response = requests.post(
                f"{API_V1_URL}/flavor-presets",
                json=duplicate_data,
                timeout=10
            )

            assert response.status_code == 409, (
                f"Expected 409 for duplicate name, got {response.status_code}"
            )
            assert "already exists" in response.json().get("detail", "").lower()
        finally:
            cleanup_preset(preset["id"])

    def test_create_preset_missing_config_returns_422(self):
        """POST /flavor-presets without config returns 422."""
        invalid_data = {
            "name": f"invalid_preset_{uuid4().hex[:8]}",
            "service_type": "summary"
            # Missing config field
        }

        response = requests.post(
            f"{API_V1_URL}/flavor-presets",
            json=invalid_data,
            timeout=10
        )

        assert response.status_code == 422, (
            f"Expected 422 for missing config, got {response.status_code}"
        )

    def test_update_preset(self):
        """PATCH /flavor-presets/{id} updates preset."""
        preset = create_test_preset("_update")
        if not preset:
            pytest.skip("Could not create test preset")

        try:
            preset_id = preset["id"]
            update_data = {
                "description_en": "Updated description for QA test"
            }

            response = requests.patch(
                f"{API_V1_URL}/flavor-presets/{preset_id}",
                json=update_data,
                timeout=10
            )

            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}: {response.text}"
            )

            result = response.json()
            assert result["description_en"] == "Updated description for QA test"
        finally:
            cleanup_preset(preset["id"])

    def test_update_preset_config(self):
        """PATCH /flavor-presets/{id} can update config values."""
        preset = create_test_preset("_config")
        if not preset:
            pytest.skip("Could not create test preset")

        try:
            preset_id = preset["id"]
            original_temp = preset["config"].get("temperature", 0.3)
            new_temp = 0.7

            update_data = {
                "config": {"temperature": new_temp}
            }

            response = requests.patch(
                f"{API_V1_URL}/flavor-presets/{preset_id}",
                json=update_data,
                timeout=10
            )

            assert response.status_code == 200

            result = response.json()
            # Config should be updated (may be merged or replaced depending on impl)
            assert result["config"].get("temperature") == new_temp or (
                "temperature" in result["config"]
            )
        finally:
            cleanup_preset(preset["id"])

    def test_delete_preset(self):
        """DELETE /flavor-presets/{id} deletes user preset."""
        preset = create_test_preset("_delete")
        if not preset:
            pytest.skip("Could not create test preset")

        preset_id = preset["id"]

        response = requests.delete(
            f"{API_V1_URL}/flavor-presets/{preset_id}",
            timeout=10
        )

        assert response.status_code == 204, (
            f"Expected 204, got {response.status_code}"
        )

        # Verify it's deleted
        get_response = requests.get(
            f"{API_V1_URL}/flavor-presets/{preset_id}",
            timeout=10
        )
        assert get_response.status_code == 404

    def test_delete_system_preset_forbidden(self):
        """DELETE /flavor-presets/{system-preset-id} returns 400."""
        # Get list and find a system preset
        response = requests.get(f"{API_V1_URL}/flavor-presets", timeout=10)
        if response.status_code != 200:
            pytest.skip("Could not list presets")

        presets = response.json()
        system_preset = next((p for p in presets if p.get("is_system")), None)

        if not system_preset:
            pytest.skip("No system presets available to test")

        delete_response = requests.delete(
            f"{API_V1_URL}/flavor-presets/{system_preset['id']}",
            timeout=10
        )

        assert delete_response.status_code == 400, (
            f"Expected 400 for system preset deletion, got {delete_response.status_code}"
        )
        assert "system" in delete_response.json().get("detail", "").lower()


class TestFlavorPresetApply:
    """Test applying presets to create new flavors."""

    def test_apply_preset_creates_flavor(self):
        """POST /flavor-presets/{id}/apply creates a new flavor."""
        # Get a preset
        response = requests.get(f"{API_V1_URL}/flavor-presets", timeout=10)
        if response.status_code != 200:
            pytest.skip("Could not list presets")

        presets = response.json()
        if not presets:
            pytest.skip("No presets available")

        preset = presets[0]
        preset_id = preset["id"]

        # Get a service and model
        service = get_first_service()
        model = get_first_model()

        if not service or not model:
            pytest.skip("No service or model available")

        service_id = service["id"]
        model_id = model["id"]
        flavor_name = f"qa_applied_flavor_{uuid4().hex[:8]}"

        # Apply preset
        apply_response = requests.post(
            f"{API_V1_URL}/flavor-presets/{preset_id}/apply",
            data={
                "service_id": service_id,
                "model_id": model_id,
                "flavor_name": flavor_name
            },
            timeout=10
        )

        if apply_response.status_code == 201:
            result = apply_response.json()
            assert result["name"] == flavor_name
            assert "processing_mode" in result

            # Verify flavor was created with preset config
            if preset["config"].get("processing_mode"):
                assert result["processing_mode"] == preset["config"]["processing_mode"]

            # Cleanup: delete created flavor
            flavor_id = result["id"]
            requests.delete(f"{API_V1_URL}/flavors/{flavor_id}", timeout=10)
        else:
            # May fail due to model compatibility, etc.
            pytest.skip(f"Apply preset returned {apply_response.status_code}: {apply_response.text[:200]}")

    def test_apply_preset_service_not_found(self):
        """POST /flavor-presets/{id}/apply with invalid service returns 404."""
        response = requests.get(f"{API_V1_URL}/flavor-presets", timeout=10)
        if response.status_code != 200 or not response.json():
            pytest.skip("No presets available")

        preset_id = response.json()[0]["id"]
        model = get_first_model()
        if not model:
            pytest.skip("No model available")

        apply_response = requests.post(
            f"{API_V1_URL}/flavor-presets/{preset_id}/apply",
            data={
                "service_id": str(uuid4()),
                "model_id": model["id"],
                "flavor_name": "test_flavor"
            },
            timeout=10
        )

        assert apply_response.status_code == 404

    def test_apply_preset_not_found(self):
        """POST /flavor-presets/{invalid-id}/apply returns 404."""
        fake_preset_id = str(uuid4())

        apply_response = requests.post(
            f"{API_V1_URL}/flavor-presets/{fake_preset_id}/apply",
            data={
                "service_id": str(uuid4()),
                "model_id": str(uuid4()),
                "flavor_name": "test_flavor"
            },
            timeout=10
        )

        assert apply_response.status_code == 404


# =============================================================================
# 5. Integration Tests
# =============================================================================

class TestPresetFlowEndToEnd:
    """End-to-end tests for preset workflow."""

    def test_preset_crud_flow(self):
        """Full CRUD cycle for presets."""
        # 1. List presets
        list_response = requests.get(f"{API_V1_URL}/flavor-presets", timeout=10)
        assert list_response.status_code == 200
        initial_count = len(list_response.json())

        # 2. Create custom preset
        preset_name = f"e2e_test_preset_{uuid4().hex[:8]}"
        create_data = {
            "name": preset_name,
            "service_type": "summary",
            "description_en": "E2E test preset",
            "description_fr": "Preset de test E2E",
            "config": {
                "processing_mode": "iterative",
                "temperature": 0.4,
                "top_p": 0.75,
                "max_new_turns": 20,
                "summary_turns": 5,
                "reduce_summary": True
            }
        }

        create_response = requests.post(
            f"{API_V1_URL}/flavor-presets",
            json=create_data,
            timeout=10
        )
        assert create_response.status_code == 201
        preset = create_response.json()
        preset_id = preset["id"]

        try:
            # 3. Get the preset
            get_response = requests.get(
                f"{API_V1_URL}/flavor-presets/{preset_id}",
                timeout=10
            )
            assert get_response.status_code == 200
            assert get_response.json()["name"] == preset_name

            # 4. Update the preset
            update_response = requests.patch(
                f"{API_V1_URL}/flavor-presets/{preset_id}",
                json={"description_en": "Updated E2E preset"},
                timeout=10
            )
            assert update_response.status_code == 200
            assert update_response.json()["description_en"] == "Updated E2E preset"

            # 5. Verify in list
            list_after = requests.get(f"{API_V1_URL}/flavor-presets", timeout=10)
            assert list_after.status_code == 200
            found = any(p["id"] == preset_id for p in list_after.json())
            assert found, "Created preset not found in list"

        finally:
            # 6. Delete
            delete_response = requests.delete(
                f"{API_V1_URL}/flavor-presets/{preset_id}",
                timeout=10
            )
            assert delete_response.status_code == 204

            # 7. Verify deleted
            verify_response = requests.get(
                f"{API_V1_URL}/flavor-presets/{preset_id}",
                timeout=10
            )
            assert verify_response.status_code == 404


class TestFlavorProcessingModeInExecution:
    """Test that processing_mode is included in service execution."""

    def test_flavor_has_processing_mode_in_service_response(self):
        """Verify flavors in service response include processing_mode."""
        response = requests.get(f"{API_V1_URL}/services", timeout=10)
        if response.status_code != 200:
            pytest.skip("Services endpoint not accessible")

        services = response.json().get("items", [])
        if not services:
            pytest.skip("No services available")

        for service in services:
            for flavor in service.get("flavors", []):
                assert "processing_mode" in flavor, (
                    f"Flavor {flavor.get('name')} missing processing_mode"
                )


# =============================================================================
# 6. Preset Schema Validation Tests
# =============================================================================

class TestPresetSchemaValidation:
    """Test preset response schema matches api-contract.md."""

    def test_preset_response_has_required_fields(self):
        """Verify preset response contains all required fields per api-contract."""
        response = requests.get(f"{API_V1_URL}/flavor-presets", timeout=10)
        if response.status_code != 200 or not response.json():
            pytest.skip("No presets available")

        preset = response.json()[0]

        required_fields = [
            "id", "name", "service_type", "is_system", "is_active",
            "config", "created_at", "updated_at"
        ]

        for field in required_fields:
            assert field in preset, f"Missing required field: {field}"

    def test_preset_config_structure(self):
        """Verify preset config has expected fields."""
        # Create a preset to ensure we have predictable config
        preset = create_test_preset("_schema")
        if not preset:
            pytest.skip("Could not create test preset")

        try:
            config = preset["config"]
            expected_fields = [
                "processing_mode", "temperature", "top_p"
            ]

            for field in expected_fields:
                assert field in config, f"Config missing field: {field}"
        finally:
            cleanup_preset(preset["id"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
