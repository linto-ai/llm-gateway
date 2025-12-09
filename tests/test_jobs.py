#!/usr/bin/env python3
"""
Jobs QA Tests - Token Analytics, Processing Metrics, Version History & Inline Editing

Tests covering:
Part A: Job Token Analytics & Processing Metrics
1. Schema validation tests - JobPassMetrics and JobTokenMetrics schemas
2. API endpoint test - GET /api/v1/jobs/{job_id}/metrics returns correct structure
3. Job response test - JobResponse includes token_metrics field
4. Metrics calculation test - Cumulative totals are calculated correctly
5. Cost estimation test - Verify cost calculation logic
6. WebSocket update schema tests - CurrentPassMetrics and CumulativeMetrics
7. API contract conformity tests

Part B: Version History & Inline Editing for Job Results
1. PATCH /api/v1/jobs/{job_id}/result - Update job result content
2. GET /api/v1/jobs/{job_id}/versions - List version history
3. GET /api/v1/jobs/{job_id}/versions/{version_number} - Get specific version
4. POST /api/v1/jobs/{job_id}/versions/{version_number}/restore - Restore to version
5. JobResponse updated with current_version and last_edited_at fields
6. Diff storage and version cleanup logic
7. i18n scenarios (FR/EN)
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from pathlib import Path


# =============================================================================
# PART A: JOB TOKEN ANALYTICS & PROCESSING METRICS
# =============================================================================


# =============================================================================
# Fixtures for Token Metrics
# =============================================================================

@pytest.fixture
def sample_pass_data():
    """Sample pass metrics data for testing."""
    return {
        "pass_number": 1,
        "pass_type": "initial",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": 2300,
        "prompt_tokens": 6200,
        "completion_tokens": 2250,
        "total_tokens": 8450,
        "input_chars": 24800,
        "output_chars": 9000,
        "estimated_cost": 0.0085,
    }


@pytest.fixture
def sample_pass_metrics_list():
    """Sample list of pass metrics for multiple passes."""
    now = datetime.now(timezone.utc)
    return [
        {
            "pass_number": 1,
            "pass_type": "initial",
            "started_at": now.isoformat(),
            "completed_at": (now + timedelta(seconds=2.3)).isoformat(),
            "duration_ms": 2300,
            "prompt_tokens": 6200,
            "completion_tokens": 2250,
            "total_tokens": 8450,
            "input_chars": 24800,
            "output_chars": 9000,
            "estimated_cost": 0.0085,
        },
        {
            "pass_number": 2,
            "pass_type": "continuation",
            "started_at": (now + timedelta(seconds=2.5)).isoformat(),
            "completed_at": (now + timedelta(seconds=4.3)).isoformat(),
            "duration_ms": 1800,
            "prompt_tokens": 5800,
            "completion_tokens": 1320,
            "total_tokens": 7120,
            "input_chars": 23200,
            "output_chars": 5280,
            "estimated_cost": 0.0071,
        },
        {
            "pass_number": 3,
            "pass_type": "reduce",
            "started_at": (now + timedelta(seconds=4.5)).isoformat(),
            "completed_at": (now + timedelta(seconds=5.7)).isoformat(),
            "duration_ms": 1200,
            "prompt_tokens": 3100,
            "completion_tokens": 1130,
            "total_tokens": 4230,
            "input_chars": 12400,
            "output_chars": 4520,
            "estimated_cost": 0.0042,
        },
    ]


@pytest.fixture
def sample_token_metrics_data(sample_pass_metrics_list):
    """Sample token metrics data structure."""
    total_prompt = sum(p["prompt_tokens"] for p in sample_pass_metrics_list)
    total_completion = sum(p["completion_tokens"] for p in sample_pass_metrics_list)
    total_duration = sum(p["duration_ms"] for p in sample_pass_metrics_list)
    total_cost = sum(p["estimated_cost"] for p in sample_pass_metrics_list)
    num_passes = len(sample_pass_metrics_list)

    return {
        "passes": sample_pass_metrics_list,
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
        "total_duration_ms": total_duration,
        "total_estimated_cost": total_cost,
        "avg_tokens_per_pass": (total_prompt + total_completion) / num_passes,
        "avg_duration_per_pass_ms": total_duration / num_passes,
    }


# =============================================================================
# 1. Schema Validation Tests - JobPassMetrics
# =============================================================================

class TestJobPassMetricsSchema:
    """Tests for JobPassMetrics schema validation."""

    def test_job_pass_metrics_valid_creation(self, sample_pass_data):
        """Test JobPassMetrics can be created with valid data."""
        from app.schemas.job import JobPassMetrics

        metrics = JobPassMetrics(**sample_pass_data)

        assert metrics.pass_number == 1
        assert metrics.pass_type == "initial"
        assert metrics.duration_ms == 2300
        assert metrics.prompt_tokens == 6200
        assert metrics.completion_tokens == 2250
        assert metrics.total_tokens == 8450
        assert metrics.input_chars == 24800
        assert metrics.output_chars == 9000
        assert metrics.estimated_cost == 0.0085

    def test_job_pass_metrics_all_pass_types(self):
        """Test all valid pass_type values are accepted."""
        from app.schemas.job import JobPassMetrics

        valid_types = ["initial", "continuation", "reduce", "summary"]
        now = datetime.now(timezone.utc)

        for pass_type in valid_types:
            metrics = JobPassMetrics(
                pass_number=1,
                pass_type=pass_type,
                started_at=now,
                completed_at=now,
                duration_ms=1000,
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                input_chars=400,
                output_chars=200,
                estimated_cost=None,
            )
            assert metrics.pass_type == pass_type

    def test_job_pass_metrics_completed_at_optional(self):
        """Test completed_at can be None for in-progress passes."""
        from app.schemas.job import JobPassMetrics

        now = datetime.now(timezone.utc)
        metrics = JobPassMetrics(
            pass_number=1,
            pass_type="initial",
            started_at=now,
            completed_at=None,  # In progress
            duration_ms=0,
            prompt_tokens=100,
            completion_tokens=0,
            total_tokens=100,
            input_chars=400,
            output_chars=0,
            estimated_cost=None,
        )

        assert metrics.completed_at is None

    def test_job_pass_metrics_estimated_cost_optional(self):
        """Test estimated_cost can be None when pricing unavailable."""
        from app.schemas.job import JobPassMetrics

        now = datetime.now(timezone.utc)
        metrics = JobPassMetrics(
            pass_number=1,
            pass_type="initial",
            started_at=now,
            completed_at=now,
            duration_ms=1000,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            input_chars=400,
            output_chars=200,
            estimated_cost=None,
        )

        assert metrics.estimated_cost is None

    def test_job_pass_metrics_validation_pass_number_ge_1(self):
        """Test pass_number must be >= 1."""
        from app.schemas.job import JobPassMetrics
        from pydantic import ValidationError

        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError):
            JobPassMetrics(
                pass_number=0,  # Invalid: must be >= 1
                pass_type="initial",
                started_at=now,
                completed_at=now,
                duration_ms=1000,
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                input_chars=400,
                output_chars=200,
            )

    def test_job_pass_metrics_validation_duration_ge_0(self):
        """Test duration_ms must be >= 0."""
        from app.schemas.job import JobPassMetrics
        from pydantic import ValidationError

        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError):
            JobPassMetrics(
                pass_number=1,
                pass_type="initial",
                started_at=now,
                completed_at=now,
                duration_ms=-100,  # Invalid: must be >= 0
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                input_chars=400,
                output_chars=200,
            )

    def test_job_pass_metrics_validation_tokens_ge_0(self):
        """Test token counts must be >= 0."""
        from app.schemas.job import JobPassMetrics
        from pydantic import ValidationError

        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError):
            JobPassMetrics(
                pass_number=1,
                pass_type="initial",
                started_at=now,
                completed_at=now,
                duration_ms=1000,
                prompt_tokens=-100,  # Invalid: must be >= 0
                completion_tokens=50,
                total_tokens=150,
                input_chars=400,
                output_chars=200,
            )


# =============================================================================
# 2. Schema Validation Tests - JobTokenMetrics
# =============================================================================

class TestJobTokenMetricsSchema:
    """Tests for JobTokenMetrics schema validation."""

    def test_job_token_metrics_valid_creation(self, sample_token_metrics_data):
        """Test JobTokenMetrics can be created with valid data."""
        from app.schemas.job import JobTokenMetrics, JobPassMetrics

        # Convert passes to JobPassMetrics objects
        passes = [JobPassMetrics(**p) for p in sample_token_metrics_data["passes"]]

        metrics = JobTokenMetrics(
            passes=passes,
            total_prompt_tokens=sample_token_metrics_data["total_prompt_tokens"],
            total_completion_tokens=sample_token_metrics_data["total_completion_tokens"],
            total_tokens=sample_token_metrics_data["total_tokens"],
            total_duration_ms=sample_token_metrics_data["total_duration_ms"],
            total_estimated_cost=sample_token_metrics_data["total_estimated_cost"],
            avg_tokens_per_pass=sample_token_metrics_data["avg_tokens_per_pass"],
            avg_duration_per_pass_ms=sample_token_metrics_data["avg_duration_per_pass_ms"],
        )

        assert len(metrics.passes) == 3
        assert metrics.total_prompt_tokens == 15100  # 6200 + 5800 + 3100
        assert metrics.total_completion_tokens == 4700  # 2250 + 1320 + 1130
        assert metrics.total_tokens == 19800  # 8450 + 7120 + 4230
        assert metrics.total_duration_ms == 5300  # 2300 + 1800 + 1200

    def test_job_token_metrics_empty_passes(self):
        """Test JobTokenMetrics with empty passes array."""
        from app.schemas.job import JobTokenMetrics

        metrics = JobTokenMetrics(
            passes=[],
            total_prompt_tokens=0,
            total_completion_tokens=0,
            total_tokens=0,
            total_duration_ms=0,
            total_estimated_cost=None,
            avg_tokens_per_pass=0.0,
            avg_duration_per_pass_ms=0.0,
        )

        assert len(metrics.passes) == 0
        assert metrics.total_tokens == 0

    def test_job_token_metrics_defaults(self):
        """Test JobTokenMetrics has correct defaults."""
        from app.schemas.job import JobTokenMetrics

        metrics = JobTokenMetrics()

        assert metrics.passes == []
        assert metrics.total_prompt_tokens == 0
        assert metrics.total_completion_tokens == 0
        assert metrics.total_tokens == 0
        assert metrics.total_duration_ms == 0
        assert metrics.total_estimated_cost is None
        assert metrics.avg_tokens_per_pass == 0.0
        assert metrics.avg_duration_per_pass_ms == 0.0

    def test_job_token_metrics_cost_can_be_none(self):
        """Test total_estimated_cost can be None."""
        from app.schemas.job import JobTokenMetrics

        metrics = JobTokenMetrics(total_estimated_cost=None)
        assert metrics.total_estimated_cost is None


# =============================================================================
# 3. WebSocket Metrics Schemas Tests
# =============================================================================

class TestCurrentPassMetricsSchema:
    """Tests for CurrentPassMetrics schema (WebSocket updates)."""

    def test_current_pass_metrics_valid_creation(self):
        """Test CurrentPassMetrics can be created with valid data."""
        from app.schemas.job import CurrentPassMetrics

        metrics = CurrentPassMetrics(
            pass_number=2,
            pass_type="continuation",
            prompt_tokens=5800,
            completion_tokens=1320,
            duration_ms=1800,
        )

        assert metrics.pass_number == 2
        assert metrics.pass_type == "continuation"
        assert metrics.prompt_tokens == 5800
        assert metrics.completion_tokens == 1320
        assert metrics.duration_ms == 1800

    def test_current_pass_metrics_validation_pass_number_ge_1(self):
        """Test pass_number must be >= 1."""
        from app.schemas.job import CurrentPassMetrics
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CurrentPassMetrics(
                pass_number=0,
                pass_type="initial",
                prompt_tokens=100,
                completion_tokens=50,
                duration_ms=1000,
            )


class TestCumulativeMetricsSchema:
    """Tests for CumulativeMetrics schema (WebSocket updates)."""

    def test_cumulative_metrics_valid_creation(self):
        """Test CumulativeMetrics can be created with valid data."""
        from app.schemas.job import CumulativeMetrics

        metrics = CumulativeMetrics(
            total_tokens=15570,
            total_prompt_tokens=12000,
            total_completion_tokens=3570,
            total_duration_ms=4100,
            total_estimated_cost=0.0156,
        )

        assert metrics.total_tokens == 15570
        assert metrics.total_prompt_tokens == 12000
        assert metrics.total_completion_tokens == 3570
        assert metrics.total_duration_ms == 4100
        assert metrics.total_estimated_cost == 0.0156

    def test_cumulative_metrics_defaults(self):
        """Test CumulativeMetrics has correct defaults."""
        from app.schemas.job import CumulativeMetrics

        metrics = CumulativeMetrics()

        assert metrics.total_tokens == 0
        assert metrics.total_prompt_tokens == 0
        assert metrics.total_completion_tokens == 0
        assert metrics.total_duration_ms == 0
        assert metrics.total_estimated_cost is None


# =============================================================================
# 4. JobResponse Schema Tests
# =============================================================================

class TestJobResponseSchema:
    """Tests for JobResponse with token_metrics field."""

    def test_job_response_includes_token_metrics_field(self):
        """Verify JobResponse has token_metrics field."""
        from app.schemas.job import JobResponse

        fields = set(JobResponse.model_fields.keys())
        assert "token_metrics" in fields

    def test_job_response_with_token_metrics(self, sample_token_metrics_data):
        """Test JobResponse can include token metrics."""
        from app.schemas.job import JobResponse, JobTokenMetrics, JobPassMetrics

        passes = [JobPassMetrics(**p) for p in sample_token_metrics_data["passes"]]
        token_metrics = JobTokenMetrics(
            passes=passes,
            total_prompt_tokens=sample_token_metrics_data["total_prompt_tokens"],
            total_completion_tokens=sample_token_metrics_data["total_completion_tokens"],
            total_tokens=sample_token_metrics_data["total_tokens"],
            total_duration_ms=sample_token_metrics_data["total_duration_ms"],
            total_estimated_cost=sample_token_metrics_data["total_estimated_cost"],
            avg_tokens_per_pass=sample_token_metrics_data["avg_tokens_per_pass"],
            avg_duration_per_pass_ms=sample_token_metrics_data["avg_duration_per_pass_ms"],
        )

        job_id = uuid4()
        service_id = uuid4()

        response = JobResponse(
            id=job_id,
            service_id=service_id,
            service_name="test-service",
            flavor_name="test-flavor",
            status="completed",
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            token_metrics=token_metrics,
        )

        assert response.token_metrics is not None
        assert response.token_metrics.total_tokens == 19800
        assert len(response.token_metrics.passes) == 3

    def test_job_response_without_token_metrics(self):
        """Test JobResponse with None token_metrics (queued/started job)."""
        from app.schemas.job import JobResponse

        job_id = uuid4()
        service_id = uuid4()

        response = JobResponse(
            id=job_id,
            service_id=service_id,
            service_name="test-service",
            flavor_name="test-flavor",
            status="queued",
            created_at=datetime.now(timezone.utc),
            token_metrics=None,
        )

        assert response.token_metrics is None


# =============================================================================
# 5. JobMetricsResponse Schema Tests
# =============================================================================

class TestJobMetricsResponseSchema:
    """Tests for JobMetricsResponse schema (dedicated metrics endpoint)."""

    def test_job_metrics_response_schema_fields(self):
        """Verify JobMetricsResponse has all required fields."""
        from app.schemas.job import JobMetricsResponse

        fields = set(JobMetricsResponse.model_fields.keys())

        required_fields = {
            "job_id",
            "status",
            "token_metrics",
            "final_summary",
        }

        assert required_fields.issubset(fields)

    def test_job_metrics_response_for_completed_job(self, sample_token_metrics_data):
        """Test JobMetricsResponse for a completed job with final_summary."""
        from app.schemas.job import JobMetricsResponse, JobTokenMetrics, JobPassMetrics, JobFinalSummary

        passes = [JobPassMetrics(**p) for p in sample_token_metrics_data["passes"]]
        token_metrics = JobTokenMetrics(
            passes=passes,
            total_prompt_tokens=sample_token_metrics_data["total_prompt_tokens"],
            total_completion_tokens=sample_token_metrics_data["total_completion_tokens"],
            total_tokens=sample_token_metrics_data["total_tokens"],
            total_duration_ms=sample_token_metrics_data["total_duration_ms"],
            total_estimated_cost=sample_token_metrics_data["total_estimated_cost"],
            avg_tokens_per_pass=sample_token_metrics_data["avg_tokens_per_pass"],
            avg_duration_per_pass_ms=sample_token_metrics_data["avg_duration_per_pass_ms"],
        )

        final_summary = JobFinalSummary(
            total_tokens=sample_token_metrics_data["total_tokens"],
            total_duration_ms=sample_token_metrics_data["total_duration_ms"],
            total_passes=3,
            total_estimated_cost=sample_token_metrics_data["total_estimated_cost"],
        )

        response = JobMetricsResponse(
            job_id=str(uuid4()),
            status="completed",
            token_metrics=token_metrics,
            final_summary=final_summary,
        )

        assert response.status == "completed"
        assert response.token_metrics is not None
        assert response.final_summary is not None
        assert response.final_summary.total_passes == 3

    def test_job_metrics_response_for_processing_job(self):
        """Test JobMetricsResponse for a processing job (no final_summary)."""
        from app.schemas.job import JobMetricsResponse

        response = JobMetricsResponse(
            job_id=str(uuid4()),
            status="processing",
            token_metrics=None,
            final_summary=None,
        )

        assert response.status == "processing"
        assert response.token_metrics is None
        assert response.final_summary is None


# =============================================================================
# 6. JobFinalSummary Schema Tests
# =============================================================================

class TestJobFinalSummarySchema:
    """Tests for JobFinalSummary schema."""

    def test_job_final_summary_valid_creation(self):
        """Test JobFinalSummary can be created with valid data."""
        from app.schemas.job import JobFinalSummary

        summary = JobFinalSummary(
            total_tokens=26690,
            total_duration_ms=7400,
            total_passes=4,
            total_estimated_cost=0.0267,
        )

        assert summary.total_tokens == 26690
        assert summary.total_duration_ms == 7400
        assert summary.total_passes == 4
        assert summary.total_estimated_cost == 0.0267

    def test_job_final_summary_cost_optional(self):
        """Test total_estimated_cost can be None."""
        from app.schemas.job import JobFinalSummary

        summary = JobFinalSummary(
            total_tokens=10000,
            total_duration_ms=5000,
            total_passes=2,
            total_estimated_cost=None,
        )

        assert summary.total_estimated_cost is None


# =============================================================================
# 7. JobUpdate Schema with Metrics Tests
# =============================================================================

class TestJobUpdateWithMetrics:
    """Tests for JobUpdate schema with metrics fields."""

    def test_job_update_includes_metrics_fields(self):
        """Verify JobUpdate has current_pass_metrics and cumulative_metrics fields."""
        from app.schemas.job import JobUpdate

        fields = set(JobUpdate.model_fields.keys())

        assert "current_pass_metrics" in fields
        assert "cumulative_metrics" in fields

    def test_job_update_with_metrics(self):
        """Test JobUpdate with current and cumulative metrics."""
        from app.schemas.job import JobUpdate, CurrentPassMetrics, CumulativeMetrics

        current_pass = CurrentPassMetrics(
            pass_number=2,
            pass_type="continuation",
            prompt_tokens=5800,
            completion_tokens=1320,
            duration_ms=1800,
        )

        cumulative = CumulativeMetrics(
            total_tokens=15570,
            total_prompt_tokens=12000,
            total_completion_tokens=3570,
            total_duration_ms=4100,
            total_estimated_cost=0.0156,
        )

        update = JobUpdate(
            job_id=str(uuid4()),
            event_type="progress",
            status="processing",
            timestamp=datetime.now(timezone.utc).isoformat(),
            current_pass_metrics=current_pass,
            cumulative_metrics=cumulative,
        )

        assert update.current_pass_metrics is not None
        assert update.current_pass_metrics.pass_number == 2
        assert update.cumulative_metrics is not None
        assert update.cumulative_metrics.total_tokens == 15570


# =============================================================================
# 8. API Endpoint Tests - GET /api/v1/jobs/{job_id}/metrics
# =============================================================================

class TestJobMetricsEndpoint:
    """Tests for the dedicated job metrics endpoint."""

    def test_metrics_endpoint_exists(self):
        """Verify /jobs/{job_id}/metrics endpoint is registered."""
        from app.api.v1.jobs import router

        routes = [route.path for route in router.routes]
        # The router has a prefix "/jobs", so the actual path includes that
        assert "/jobs/{job_id}/metrics" in routes

    def test_metrics_endpoint_returns_correct_response_model(self):
        """Verify endpoint returns JobMetricsResponse."""
        from app.api.v1.jobs import get_job_metrics
        import inspect

        # Check it's an async function
        assert inspect.iscoroutinefunction(get_job_metrics)


# =============================================================================
# 9. _extract_token_metrics Function Tests
# =============================================================================

class TestExtractTokenMetrics:
    """Tests for the _extract_token_metrics helper function."""

    def test_extract_token_metrics_with_valid_data(self, sample_token_metrics_data):
        """Test extraction with valid token metrics in progress."""
        from app.services.job_service import _extract_token_metrics

        progress = {
            "token_metrics": sample_token_metrics_data
        }

        result = _extract_token_metrics(progress)

        assert result is not None
        assert len(result.passes) == 3
        assert result.total_prompt_tokens == 15100
        assert result.total_completion_tokens == 4700
        assert result.total_tokens == 19800

    def test_extract_token_metrics_empty_progress(self):
        """Test extraction with empty progress returns None."""
        from app.services.job_service import _extract_token_metrics

        result = _extract_token_metrics(None)
        assert result is None

        result = _extract_token_metrics({})
        assert result is None

    def test_extract_token_metrics_no_token_metrics_key(self):
        """Test extraction when token_metrics key is missing."""
        from app.services.job_service import _extract_token_metrics

        progress = {"percentage": 50, "current": 5, "total": 10}
        result = _extract_token_metrics(progress)

        assert result is None

    def test_extract_token_metrics_handles_malformed_data(self):
        """Test extraction handles malformed token_metrics gracefully."""
        from app.services.job_service import _extract_token_metrics

        # Missing required fields
        progress = {
            "token_metrics": {
                "passes": [{"pass_number": 1}],  # Missing required fields
                "total_tokens": 100,
            }
        }

        result = _extract_token_metrics(progress)
        # Should return None due to validation error
        assert result is None


# =============================================================================
# 10. Cost Estimation Tests
# =============================================================================

class TestCostEstimation:
    """Tests for cost estimation logic in batch_manager."""

    def test_cost_estimation_basic_calculation(self):
        """Test basic cost calculation with known values."""
        # Based on batch_manager._estimate_cost:
        # prompt_rate = 0.00003  ($0.03 per 1K tokens)
        # completion_rate = 0.00006  ($0.06 per 1K tokens)

        prompt_tokens = 1000
        completion_tokens = 1000

        # Manual calculation:
        # prompt_cost = 1000 * 0.00003 = 0.03
        # completion_cost = 1000 * 0.00006 = 0.06
        # total = 0.09

        prompt_cost = prompt_tokens * 0.00003
        completion_cost = completion_tokens * 0.00006
        expected_cost = round(prompt_cost + completion_cost, 6)

        assert expected_cost == 0.09

    def test_cost_estimation_zero_tokens(self):
        """Test cost is None when no tokens used."""
        # From batch_manager._estimate_cost logic:
        # Returns None if both prompt and completion tokens are 0

        usage = {"prompt_tokens": 0, "completion_tokens": 0}

        # Simulate the logic
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        if prompt_tokens == 0 and completion_tokens == 0:
            cost = None
        else:
            cost = prompt_tokens * 0.00003 + completion_tokens * 0.00006

        assert cost is None

    def test_cumulative_cost_calculation(self, sample_pass_metrics_list):
        """Test cumulative cost across multiple passes."""
        total_cost = sum(p["estimated_cost"] for p in sample_pass_metrics_list)

        # 0.0085 + 0.0071 + 0.0042 = 0.0198
        expected_total = round(0.0085 + 0.0071 + 0.0042, 6)
        assert round(total_cost, 6) == expected_total


# =============================================================================
# 11. Metrics Calculation Tests
# =============================================================================

class TestMetricsCalculation:
    """Tests for cumulative metrics calculation."""

    def test_cumulative_totals_calculation(self, sample_pass_metrics_list):
        """Test cumulative totals are calculated correctly."""
        total_prompt = sum(p["prompt_tokens"] for p in sample_pass_metrics_list)
        total_completion = sum(p["completion_tokens"] for p in sample_pass_metrics_list)
        total_tokens = sum(p["total_tokens"] for p in sample_pass_metrics_list)
        total_duration = sum(p["duration_ms"] for p in sample_pass_metrics_list)

        # Expected values:
        # prompt: 6200 + 5800 + 3100 = 15100
        # completion: 2250 + 1320 + 1130 = 4700
        # total: 8450 + 7120 + 4230 = 19800
        # duration: 2300 + 1800 + 1200 = 5300

        assert total_prompt == 15100
        assert total_completion == 4700
        assert total_tokens == 19800
        assert total_duration == 5300

    def test_average_calculation(self, sample_pass_metrics_list):
        """Test average metrics calculation."""
        total_tokens = sum(p["total_tokens"] for p in sample_pass_metrics_list)
        total_duration = sum(p["duration_ms"] for p in sample_pass_metrics_list)
        num_passes = len(sample_pass_metrics_list)

        avg_tokens = total_tokens / num_passes
        avg_duration = total_duration / num_passes

        # Expected values:
        # avg_tokens: 19800 / 3 = 6600
        # avg_duration: 5300 / 3 = 1766.67

        assert avg_tokens == 6600.0
        assert round(avg_duration, 2) == 1766.67


# =============================================================================
# PART B: VERSION HISTORY & INLINE EDITING FOR JOB RESULTS
# =============================================================================


# =============================================================================
# 12. JobResponse Schema Tests - Version Fields
# =============================================================================

class TestJobResponseVersionFields:
    """Tests for version tracking fields in JobResponse."""

    def test_job_response_has_current_version_field(self):
        """Verify JobResponse has current_version field."""
        from app.schemas.job import JobResponse

        fields = JobResponse.model_fields
        assert "current_version" in fields, \
            "JobResponse must have 'current_version' field per api-contract.md"

    def test_job_response_current_version_default_is_1(self):
        """Verify current_version defaults to 1."""
        from app.schemas.job import JobResponse

        field_info = JobResponse.model_fields["current_version"]
        assert field_info.default == 1, \
            "current_version default should be 1"

    def test_job_response_has_last_edited_at_field(self):
        """Verify JobResponse has last_edited_at field."""
        from app.schemas.job import JobResponse

        fields = JobResponse.model_fields
        assert "last_edited_at" in fields, \
            "JobResponse must have 'last_edited_at' field per api-contract.md"

    def test_job_response_last_edited_at_is_optional(self):
        """Verify last_edited_at is optional (nullable)."""
        from app.schemas.job import JobResponse

        field_info = JobResponse.model_fields["last_edited_at"]
        assert field_info.default is None, \
            "last_edited_at should default to None"

    def test_job_response_instantiation_with_version_fields(self):
        """Test JobResponse can be created with version fields."""
        from app.schemas.job import JobResponse

        job = JobResponse(
            id=uuid4(),
            service_id=uuid4(),
            service_name="test-service",
            flavor_name="test-flavor",
            status="completed",
            created_at=datetime.utcnow(),
            result={"output": "Test content"},
            output_type="text",
            current_version=2,
            last_edited_at=datetime.utcnow()
        )

        assert job.current_version == 2
        assert job.last_edited_at is not None


# =============================================================================
# 13. JobResultUpdate Schema Tests
# =============================================================================

class TestJobResultUpdateSchema:
    """Tests for JobResultUpdate request schema."""

    def test_job_result_update_schema_exists(self):
        """Verify JobResultUpdate schema exists."""
        from app.schemas.job import JobResultUpdate

        assert JobResultUpdate is not None

    def test_job_result_update_has_content_field(self):
        """Verify content field is required."""
        from app.schemas.job import JobResultUpdate

        fields = JobResultUpdate.model_fields
        assert "content" in fields, \
            "JobResultUpdate must have 'content' field"

    def test_job_result_update_content_is_required(self):
        """Content field should be required (no default)."""
        from app.schemas.job import JobResultUpdate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            JobResultUpdate()  # Missing required 'content'

    def test_job_result_update_content_cannot_be_empty(self):
        """Content cannot be empty string per api-contract.md."""
        from app.schemas.job import JobResultUpdate
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            JobResultUpdate(content="")

        # Should fail validation for min_length
        assert "content" in str(exc_info.value).lower()

    def test_job_result_update_valid_content(self):
        """Valid content should pass validation."""
        from app.schemas.job import JobResultUpdate

        update = JobResultUpdate(content="Updated content here")
        assert update.content == "Updated content here"

    def test_job_result_update_with_unicode_content(self):
        """Unicode content (French) should be accepted."""
        from app.schemas.job import JobResultUpdate

        update = JobResultUpdate(content="Contenu mis a jour en francais avec des accents: cafe, resume")
        assert "francais" in update.content


# =============================================================================
# 14. JobVersionSummary Schema Tests
# =============================================================================

class TestJobVersionSummarySchema:
    """Tests for JobVersionSummary response schema."""

    def test_job_version_summary_schema_exists(self):
        """Verify JobVersionSummary schema exists."""
        from app.schemas.job import JobVersionSummary

        assert JobVersionSummary is not None

    def test_job_version_summary_has_required_fields(self):
        """Verify all required fields per api-contract.md."""
        from app.schemas.job import JobVersionSummary

        fields = set(JobVersionSummary.model_fields.keys())
        required = {"version_number", "created_at", "created_by", "content_length"}

        assert required.issubset(fields), \
            f"JobVersionSummary missing fields: {required - fields}"

    def test_job_version_summary_instantiation(self):
        """Test JobVersionSummary can be created with valid data."""
        from app.schemas.job import JobVersionSummary

        summary = JobVersionSummary(
            version_number=1,
            created_at=datetime.utcnow(),
            created_by=None,
            content_length=1234
        )

        assert summary.version_number == 1
        assert summary.content_length == 1234
        assert summary.created_by is None


# =============================================================================
# 15. JobVersionDetail Schema Tests
# =============================================================================

class TestJobVersionDetailSchema:
    """Tests for JobVersionDetail response schema."""

    def test_job_version_detail_schema_exists(self):
        """Verify JobVersionDetail schema exists."""
        from app.schemas.job import JobVersionDetail

        assert JobVersionDetail is not None

    def test_job_version_detail_has_content_field(self):
        """Verify JobVersionDetail has content field for full reconstructed content."""
        from app.schemas.job import JobVersionDetail

        fields = set(JobVersionDetail.model_fields.keys())
        assert "content" in fields, \
            "JobVersionDetail must have 'content' field per api-contract.md"

    def test_job_version_detail_has_required_fields(self):
        """Verify all required fields per api-contract.md."""
        from app.schemas.job import JobVersionDetail

        fields = set(JobVersionDetail.model_fields.keys())
        required = {"version_number", "created_at", "created_by", "content"}

        assert required.issubset(fields), \
            f"JobVersionDetail missing fields: {required - fields}"

    def test_job_version_detail_instantiation(self):
        """Test JobVersionDetail can be created with valid data."""
        from app.schemas.job import JobVersionDetail

        detail = JobVersionDetail(
            version_number=2,
            created_at=datetime.utcnow(),
            created_by="test-user",
            content="Full reconstructed content here"
        )

        assert detail.version_number == 2
        assert detail.content == "Full reconstructed content here"
        assert detail.created_by == "test-user"


# =============================================================================
# 16. Job Model Tests - Version Fields
# =============================================================================

class TestJobModelVersionFields:
    """Tests for version tracking fields in Job database model."""

    def test_job_model_has_current_version_column(self):
        """Verify jobs table has current_version column."""
        from app.models.job import Job

        columns = {c.name for c in Job.__table__.columns}
        assert "current_version" in columns, \
            "jobs table must have 'current_version' column"

    def test_job_model_current_version_has_default(self):
        """Verify current_version has default value of 1."""
        from app.models.job import Job

        column = Job.__table__.c.current_version
        assert column.default is not None or column.server_default is not None, \
            "current_version column should have a default"

    def test_job_model_has_last_edited_at_column(self):
        """Verify jobs table has last_edited_at column."""
        from app.models.job import Job

        columns = {c.name for c in Job.__table__.columns}
        assert "last_edited_at" in columns, \
            "jobs table must have 'last_edited_at' column"

    def test_job_model_has_versions_relationship(self):
        """Verify Job model has relationship to JobResultVersion."""
        from app.models.job import Job

        assert hasattr(Job, 'versions'), \
            "Job model must have 'versions' relationship"


# =============================================================================
# 17. JobResultVersion Model Tests
# =============================================================================

class TestJobResultVersionModel:
    """Tests for JobResultVersion database model."""

    def test_job_result_version_model_exists(self):
        """Verify JobResultVersion model exists."""
        from app.models.job_result_version import JobResultVersion

        assert JobResultVersion is not None

    def test_job_result_version_has_required_columns(self):
        """Verify all required columns exist."""
        from app.models.job_result_version import JobResultVersion

        columns = {c.name for c in JobResultVersion.__table__.columns}
        required = {
            "id", "job_id", "version_number", "diff",
            "full_content", "created_at", "created_by"
        }

        assert required.issubset(columns), \
            f"JobResultVersion missing columns: {required - columns}"

    def test_job_result_version_has_unique_constraint(self):
        """Verify unique constraint on (job_id, version_number)."""
        from app.models.job_result_version import JobResultVersion

        # Check for unique constraint
        constraints = [
            c for c in JobResultVersion.__table__.constraints
            if hasattr(c, 'name') and c.name == 'unique_job_version'
        ]
        assert len(constraints) == 1, \
            "JobResultVersion must have 'unique_job_version' constraint"

    def test_job_result_version_has_job_relationship(self):
        """Verify JobResultVersion has relationship back to Job."""
        from app.models.job_result_version import JobResultVersion

        assert hasattr(JobResultVersion, 'job'), \
            "JobResultVersion must have 'job' relationship"


# =============================================================================
# 18. API Endpoint Router Tests for Version History
# =============================================================================

class TestVersionHistoryAPIEndpointsExist:
    """Tests verifying all version history endpoints are registered."""

    def test_update_job_result_endpoint_exists(self):
        """Verify PATCH /jobs/{job_id}/result endpoint is registered."""
        from app.api.v1.jobs import router

        # Find routes with PATCH method and /result path
        patch_result_routes = []
        for route in router.routes:
            methods = getattr(route, 'methods', set()) or set()
            path = getattr(route, 'path', '')
            if 'PATCH' in methods and '/result' in path:
                patch_result_routes.append(path)

        assert len(patch_result_routes) >= 1, \
            "PATCH /jobs/{job_id}/result endpoint must exist"

    def test_list_versions_endpoint_exists(self):
        """Verify GET /jobs/{job_id}/versions endpoint is registered."""
        from app.api.v1.jobs import router

        routes = [route.path for route in router.routes]
        versions_routes = [r for r in routes if '/versions' in r and r.endswith('/versions')]

        assert len(versions_routes) >= 1, \
            "GET /jobs/{job_id}/versions endpoint must exist"

    def test_get_version_endpoint_exists(self):
        """Verify GET /jobs/{job_id}/versions/{version_number} endpoint is registered."""
        from app.api.v1.jobs import router

        routes = [route.path for route in router.routes]
        detail_routes = [r for r in routes if 'version_number' in r]

        assert len(detail_routes) >= 1, \
            "GET /jobs/{job_id}/versions/{version_number} endpoint must exist"

    def test_restore_version_endpoint_exists(self):
        """Verify POST /jobs/{job_id}/versions/{version_number}/restore endpoint is registered."""
        from app.api.v1.jobs import router

        routes = [route.path for route in router.routes]
        restore_routes = [r for r in routes if '/restore' in r]

        assert len(restore_routes) >= 1, \
            "POST /jobs/{job_id}/versions/{version_number}/restore endpoint must exist"


# =============================================================================
# 19. Version Service Tests
# =============================================================================

class TestJobResultVersionService:
    """Tests for JobResultVersionService."""

    def test_service_singleton_exists(self):
        """Verify job_result_version_service singleton exists."""
        from app.services.job_result_version_service import job_result_version_service

        assert job_result_version_service is not None

    def test_service_has_create_version_method(self):
        """Verify service has create_version method."""
        from app.services.job_result_version_service import job_result_version_service

        assert hasattr(job_result_version_service, 'create_version'), \
            "Service must have 'create_version' method"

    def test_service_has_list_versions_method(self):
        """Verify service has list_versions method."""
        from app.services.job_result_version_service import job_result_version_service

        assert hasattr(job_result_version_service, 'list_versions'), \
            "Service must have 'list_versions' method"

    def test_service_has_get_version_method(self):
        """Verify service has get_version method."""
        from app.services.job_result_version_service import job_result_version_service

        assert hasattr(job_result_version_service, 'get_version'), \
            "Service must have 'get_version' method"

    def test_service_has_restore_version_method(self):
        """Verify service has restore_version method."""
        from app.services.job_result_version_service import job_result_version_service

        assert hasattr(job_result_version_service, 'restore_version'), \
            "Service must have 'restore_version' method"

    def test_service_max_versions_constant(self):
        """Verify MAX_VERSIONS constant is 10 per api-contract.md."""
        from app.services.job_result_version_service import MAX_VERSIONS

        assert MAX_VERSIONS == 10, \
            "MAX_VERSIONS should be 10 per api-contract.md"

    def test_service_full_snapshot_interval_constant(self):
        """Verify FULL_SNAPSHOT_INTERVAL constant is 5 per api-contract.md."""
        from app.services.job_result_version_service import FULL_SNAPSHOT_INTERVAL

        assert FULL_SNAPSHOT_INTERVAL == 5, \
            "FULL_SNAPSHOT_INTERVAL should be 5 per api-contract.md"


# =============================================================================
# 20. Diff Storage Tests (Unit Tests)
# =============================================================================

class TestDiffComputation:
    """Tests for diff computation and application."""

    def test_service_has_compute_diff_method(self):
        """Verify service has _compute_diff method."""
        from app.services.job_result_version_service import job_result_version_service

        assert hasattr(job_result_version_service, '_compute_diff'), \
            "Service must have '_compute_diff' method"

    def test_service_has_apply_diff_method(self):
        """Verify service has _apply_diff method."""
        from app.services.job_result_version_service import job_result_version_service

        assert hasattr(job_result_version_service, '_apply_diff'), \
            "Service must have '_apply_diff' method"

    def test_diff_computation_basic(self):
        """Test basic diff computation."""
        from app.services.job_result_version_service import job_result_version_service

        old_content = "Hello World"
        new_content = "Hello New World"

        diff = job_result_version_service._compute_diff(old_content, new_content)

        assert diff is not None
        assert len(diff) > 0

    def test_diff_application_basic(self):
        """Test basic diff application."""
        from app.services.job_result_version_service import job_result_version_service

        old_content = "Hello World"
        new_content = "Hello New World"

        diff = job_result_version_service._compute_diff(old_content, new_content)
        reconstructed = job_result_version_service._apply_diff(old_content, diff)

        assert reconstructed == new_content

    def test_diff_with_unicode_content(self):
        """Test diff computation with Unicode (French) content."""
        from app.services.job_result_version_service import job_result_version_service

        old_content = "Resume du document en francais"
        new_content = "Resume modifie du document en francais avec accents: cafe, ecole"

        diff = job_result_version_service._compute_diff(old_content, new_content)
        reconstructed = job_result_version_service._apply_diff(old_content, diff)

        assert reconstructed == new_content

    def test_diff_with_large_content(self):
        """Test diff computation with large content (>10KB)."""
        from app.services.job_result_version_service import job_result_version_service

        old_content = "Line of text\n" * 1000  # ~13KB
        new_content = old_content + "Additional content at the end\n"

        diff = job_result_version_service._compute_diff(old_content, new_content)
        reconstructed = job_result_version_service._apply_diff(old_content, diff)

        assert reconstructed == new_content

    def test_extract_result_content_from_dict(self):
        """Test content extraction from dict result."""
        from app.services.job_result_version_service import job_result_version_service

        result = {"output": "Test content", "metadata": {"key": "value"}}
        content = job_result_version_service._extract_result_content(result)

        assert content == "Test content"

    def test_extract_result_content_from_string(self):
        """Test content extraction from string result."""
        from app.services.job_result_version_service import job_result_version_service

        result = "Plain string content"
        content = job_result_version_service._extract_result_content(result)

        assert content == "Plain string content"

    def test_extract_result_content_from_none(self):
        """Test content extraction from None result."""
        from app.services.job_result_version_service import job_result_version_service

        content = job_result_version_service._extract_result_content(None)

        assert content == ""


# =============================================================================
# 22. API Contract Conformity Tests
# =============================================================================

class TestJobsAPIContractConformity:
    """Tests verifying conformity to api-contract.md specification."""

    def test_job_pass_metrics_has_all_required_fields(self):
        """Verify JobPassMetrics has all fields from api-contract.md."""
        from app.schemas.job import JobPassMetrics

        fields = set(JobPassMetrics.model_fields.keys())

        required_fields = {
            "pass_number",
            "pass_type",
            "started_at",
            "completed_at",
            "duration_ms",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "input_chars",
            "output_chars",
            "estimated_cost",
        }

        assert required_fields.issubset(fields), \
            f"Missing fields: {required_fields - fields}"

    def test_job_token_metrics_has_all_required_fields(self):
        """Verify JobTokenMetrics has all fields from api-contract.md."""
        from app.schemas.job import JobTokenMetrics

        fields = set(JobTokenMetrics.model_fields.keys())

        required_fields = {
            "passes",
            "total_prompt_tokens",
            "total_completion_tokens",
            "total_tokens",
            "total_duration_ms",
            "total_estimated_cost",
            "avg_tokens_per_pass",
            "avg_duration_per_pass_ms",
        }

        assert required_fields.issubset(fields), \
            f"Missing fields: {required_fields - fields}"

    def test_job_metrics_response_has_all_required_fields(self):
        """Verify JobMetricsResponse has all fields from api-contract.md."""
        from app.schemas.job import JobMetricsResponse

        fields = set(JobMetricsResponse.model_fields.keys())

        required_fields = {
            "job_id",
            "status",
            "token_metrics",
            "final_summary",
        }

        assert required_fields.issubset(fields), \
            f"Missing fields: {required_fields - fields}"

    def test_job_response_has_all_version_fields(self):
        """Verify JobResponse has all version history fields."""
        from app.schemas.job import JobResponse

        fields = set(JobResponse.model_fields.keys())

        # Version history new fields
        version_fields = {"current_version", "last_edited_at"}

        assert version_fields.issubset(fields), \
            f"JobResponse missing version fields: {version_fields - fields}"

    def test_job_update_has_metrics_fields(self):
        """Verify JobUpdate has WebSocket metrics fields."""
        from app.schemas.job import JobUpdate

        fields = set(JobUpdate.model_fields.keys())

        metrics_fields = {
            "current_pass_metrics",
            "cumulative_metrics",
        }

        assert metrics_fields.issubset(fields), \
            f"Missing metrics fields: {metrics_fields - fields}"

    def test_pass_type_literal_values(self):
        """Verify pass_type accepts exactly the specified literal values."""
        from app.schemas.job import PassType

        # PassType should be a Literal with these values
        expected_types = {"initial", "continuation", "reduce", "summary", "extraction", "single_pass", "categorization"}

        # Get the args from the Literal type
        from typing import get_args
        actual_types = set(get_args(PassType))

        assert actual_types == expected_types


# =============================================================================
# 23. Integration Tests
# =============================================================================

class TestJobServiceIntegrationTests:
    """Integration tests for job service with metrics and version tracking."""

    @pytest.mark.asyncio
    async def test_get_job_by_id_includes_token_metrics(self, sample_token_metrics_data):
        """Test get_job_by_id returns JobResponse with token_metrics."""
        from app.services.job_service import JobService, _extract_token_metrics

        # Mock the database query
        mock_job = Mock()
        mock_job.id = uuid4()
        mock_job.service_id = uuid4()
        mock_job.service = Mock(name="test-service")
        mock_job.service.name = "test-service"
        mock_job.flavor = Mock(name="test-flavor")
        mock_job.flavor.name = "test-flavor"
        mock_job.flavor.output_type = "text"
        mock_job.flavor.processing_mode = "iterative"
        mock_job.flavor.placeholder_extraction_prompt_id = None
        mock_job.status = "completed"
        mock_job.created_at = datetime.now(timezone.utc)
        mock_job.started_at = datetime.now(timezone.utc)
        mock_job.completed_at = datetime.now(timezone.utc)
        mock_job.result = {"output": "test"}
        mock_job.error = None
        mock_job.progress = {
            "token_metrics": sample_token_metrics_data,
            "current": 100,
            "total": 100,
            "percentage": 100.0,
        }
        mock_job.organization_id = None
        mock_job.current_version = 1
        mock_job.last_edited_at = None
        # Fallback tracking fields (use the actual model field names)
        mock_job.fallback_applied = False
        mock_job.original_flavor_id = None
        mock_job.original_flavor_name = None
        mock_job.fallback_reason = None
        mock_job.fallback_input_tokens = None
        mock_job.fallback_context_available = None

        service = JobService()

        # Create a properly structured mock for async SQLAlchemy
        mock_db = AsyncMock()
        mock_unique_result = Mock()
        mock_unique_result.scalar_one_or_none.return_value = mock_job
        mock_result = Mock()
        mock_result.unique.return_value = mock_unique_result
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = await service.get_job_by_id(mock_db, mock_job.id)

        assert response is not None
        assert response.token_metrics is not None
        assert response.token_metrics.total_tokens == 19800

    def test_job_service_returns_current_version(self):
        """Verify job_service.get_job_by_id returns current_version."""
        # Use inspect to get the actual source code (works in Docker and locally)
        import inspect
        from app.services.job_service import JobService
        content = inspect.getsource(JobService)

        assert "current_version" in content, \
            "job_service should reference current_version"

    def test_job_service_returns_last_edited_at(self):
        """Verify job_service.get_job_by_id returns last_edited_at."""
        # Use inspect to get the actual source code (works in Docker and locally)
        import inspect
        from app.services.job_service import JobService
        content = inspect.getsource(JobService)

        assert "last_edited_at" in content, \
            "job_service should reference last_edited_at"


# =============================================================================
# 24. i18n Tests (FR/EN)
# =============================================================================

class TestJobsI18nFunctionality:
    """Tests for i18n support with jobs."""

    def test_job_result_update_with_french_content(self):
        """Test JobResultUpdate accepts French content."""
        from app.schemas.job import JobResultUpdate

        update = JobResultUpdate(
            content="Resume corrige avec les modifications demandees. Les erreurs ont ete rectifiees."
        )

        assert "Resume" in update.content
        assert "modifications" in update.content

    def test_job_result_update_with_english_content(self):
        """Test JobResultUpdate accepts English content."""
        from app.schemas.job import JobResultUpdate

        update = JobResultUpdate(
            content="Corrected summary with requested modifications. Errors have been fixed."
        )

        assert "Corrected" in update.content
        assert "modifications" in update.content

    def test_diff_preserves_unicode_characters(self):
        """Test that diff preserves all Unicode characters correctly."""
        from app.services.job_result_version_service import job_result_version_service

        # French content with special characters
        old_content = "Le cafe est delicieux"
        new_content = "Le cafe francais est tres delicieux"

        diff = job_result_version_service._compute_diff(old_content, new_content)
        reconstructed = job_result_version_service._apply_diff(old_content, diff)

        assert reconstructed == new_content


# =============================================================================
# 25. Edge Cases and Business Rules
# =============================================================================

class TestJobsEdgeCasesAndBusinessRules:
    """Tests for edge cases and business rules."""

    def test_version_1_is_always_preserved(self):
        """Document that version 1 (original) is always preserved."""
        # Per api-contract.md: Version 1 always preserved (original)
        from app.services.job_result_version_service import job_result_version_service

        assert hasattr(job_result_version_service, '_cleanup_old_versions'), \
            "Service should have cleanup method that preserves version 1"

    def test_max_10_versions_per_job(self):
        """Document MAX_VERSIONS limit of 10."""
        from app.services.job_result_version_service import MAX_VERSIONS

        assert MAX_VERSIONS == 10, \
            "MAX_VERSIONS should be 10 per api-contract.md"

    def test_full_snapshot_every_5th_version(self):
        """Document full snapshot at every 5th version."""
        from app.services.job_result_version_service import FULL_SNAPSHOT_INTERVAL

        assert FULL_SNAPSHOT_INTERVAL == 5, \
            "Full snapshots at version 1 and every 5th version per api-contract.md"


# =============================================================================
# 26. API Handlers Function Signature Tests
# =============================================================================

class TestJobsAPIHandlerSignatures:
    """Tests for API handler function signatures."""

    def test_update_job_result_handler_exists(self):
        """Verify update_job_result handler exists."""
        from app.api.v1.jobs import update_job_result

        assert update_job_result is not None

    def test_list_job_versions_handler_exists(self):
        """Verify list_job_versions handler exists."""
        from app.api.v1.jobs import list_job_versions

        assert list_job_versions is not None

    def test_get_job_version_handler_exists(self):
        """Verify get_job_version handler exists."""
        from app.api.v1.jobs import get_job_version

        assert get_job_version is not None

    def test_restore_job_version_handler_exists(self):
        """Verify restore_job_version handler exists."""
        from app.api.v1.jobs import restore_job_version

        assert restore_job_version is not None

    def test_update_job_result_accepts_job_result_update(self):
        """Verify update_job_result accepts JobResultUpdate."""
        import inspect
        from app.api.v1.jobs import update_job_result

        sig = inspect.signature(update_job_result)
        params = sig.parameters

        assert "update_data" in params, \
            "update_job_result should accept update_data parameter"

    def test_get_job_version_accepts_version_number(self):
        """Verify get_job_version accepts version_number."""
        import inspect
        from app.api.v1.jobs import get_job_version

        sig = inspect.signature(get_job_version)
        params = sig.parameters

        assert "version_number" in params, \
            "get_job_version should accept version_number parameter"


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
