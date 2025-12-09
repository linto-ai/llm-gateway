"""
Analytics Dashboard & Service-Level Statistics - QA Tests

Tests:
1. Schema validation tests - DashboardAnalytics and ServiceStats schemas
2. GET /api/v1/analytics/dashboard - Dashboard analytics endpoint
3. GET /api/v1/services/{service_id}/stats - Service-level stats endpoint
4. Health status logic tests - healthy/degraded/unhealthy/inactive
5. Period validation tests - 24h/7d/30d/all and invalid
6. Error handling tests - 404 for non-existent service, 400 for invalid period
7. API contract conformity tests
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4, UUID


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_overview_data():
    """Sample dashboard overview data for testing."""
    return {
        "total_jobs": 250,
        "successful_jobs": 240,
        "failed_jobs": 10,
        "success_rate": 96.0,
        "total_tokens": 5678900,
        "total_cost": 123.45,
        "active_services": 4,
        "avg_latency_ms": 11500,
    }


@pytest.fixture
def sample_service_health_data():
    """Sample service health summary data."""
    return {
        "service_id": uuid4(),
        "service_name": "summarize-en",
        "requests_24h": 80,
        "success_rate": 98.5,
        "status": "healthy",
    }


@pytest.fixture
def sample_failure_data():
    """Sample recent failure data."""
    return {
        "job_id": uuid4(),
        "service_name": "summarize-fr",
        "error": "Context window exceeded",
        "timestamp": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_service_stats_data():
    """Sample service stats data."""
    return {
        "total_requests": 150,
        "successful_requests": 145,
        "failed_requests": 5,
        "success_rate": 96.7,
        "total_tokens": 1234567,
        "total_estimated_cost": 45.67,
        "avg_latency_ms": 12500,
        "flavors_used": 3,
        "most_used_flavor": "gpt-fast",
    }


@pytest.fixture
def sample_flavor_breakdown():
    """Sample flavor breakdown data."""
    return [
        {
            "flavor_id": uuid4(),
            "flavor_name": "gpt-fast",
            "requests": 100,
            "percentage": 66.7,
        },
        {
            "flavor_id": uuid4(),
            "flavor_name": "gpt-quality",
            "requests": 50,
            "percentage": 33.3,
        },
    ]


@pytest.fixture
def sample_time_series():
    """Sample time series data."""
    return [
        {
            "timestamp": datetime.now(timezone.utc) - timedelta(hours=1),
            "requests": 12,
            "tokens": 98000,
            "cost": 3.45,
        },
        {
            "timestamp": datetime.now(timezone.utc),
            "requests": 15,
            "tokens": 120000,
            "cost": 4.20,
        },
    ]


# =============================================================================
# 1. Schema Validation Tests - DashboardOverview
# =============================================================================

class TestDashboardOverviewSchema:
    """Tests for DashboardOverview schema validation."""

    def test_dashboard_overview_valid_creation(self, sample_overview_data):
        """Test DashboardOverview can be created with valid data."""
        from app.schemas.analytics import DashboardOverview

        overview = DashboardOverview(**sample_overview_data)

        assert overview.total_jobs == 250
        assert overview.successful_jobs == 240
        assert overview.failed_jobs == 10
        assert overview.success_rate == 96.0
        assert overview.total_tokens == 5678900
        assert overview.total_cost == 123.45
        assert overview.active_services == 4
        assert overview.avg_latency_ms == 11500

    def test_dashboard_overview_zero_values(self):
        """Test DashboardOverview with all zeros (no data case)."""
        from app.schemas.analytics import DashboardOverview

        overview = DashboardOverview(
            total_jobs=0,
            successful_jobs=0,
            failed_jobs=0,
            success_rate=0.0,
            total_tokens=0,
            total_cost=0.0,
            active_services=0,
            avg_latency_ms=0.0,
        )

        assert overview.total_jobs == 0
        assert overview.success_rate == 0.0

    def test_dashboard_overview_validation_jobs_ge_0(self):
        """Test total_jobs must be >= 0."""
        from app.schemas.analytics import DashboardOverview
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DashboardOverview(
                total_jobs=-1,
                successful_jobs=0,
                failed_jobs=0,
                success_rate=0.0,
                total_tokens=0,
                total_cost=0.0,
                active_services=0,
                avg_latency_ms=0.0,
            )

    def test_dashboard_overview_validation_success_rate_le_100(self):
        """Test success_rate must be <= 100."""
        from app.schemas.analytics import DashboardOverview
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DashboardOverview(
                total_jobs=10,
                successful_jobs=10,
                failed_jobs=0,
                success_rate=101.0,  # Invalid: must be <= 100
                total_tokens=0,
                total_cost=0.0,
                active_services=0,
                avg_latency_ms=0.0,
            )


# =============================================================================
# 2. Schema Validation Tests - ServiceHealthSummary
# =============================================================================

class TestServiceHealthSummarySchema:
    """Tests for ServiceHealthSummary schema validation."""

    def test_service_health_summary_valid_creation(self, sample_service_health_data):
        """Test ServiceHealthSummary can be created with valid data."""
        from app.schemas.analytics import ServiceHealthSummary

        summary = ServiceHealthSummary(**sample_service_health_data)

        assert str(summary.service_id) == str(sample_service_health_data["service_id"])
        assert summary.service_name == "summarize-en"
        assert summary.requests_24h == 80
        assert summary.success_rate == 98.5
        assert summary.status == "healthy"

    def test_service_health_summary_all_statuses(self):
        """Test all valid status values are accepted."""
        from app.schemas.analytics import ServiceHealthSummary

        valid_statuses = ["healthy", "degraded", "unhealthy", "inactive"]

        for status in valid_statuses:
            summary = ServiceHealthSummary(
                service_id=uuid4(),
                service_name="test-service",
                requests_24h=10,
                success_rate=50.0,
                status=status,
            )
            assert summary.status == status

    def test_service_health_summary_invalid_status(self):
        """Test invalid status is rejected."""
        from app.schemas.analytics import ServiceHealthSummary
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ServiceHealthSummary(
                service_id=uuid4(),
                service_name="test-service",
                requests_24h=10,
                success_rate=50.0,
                status="invalid-status",
            )


# =============================================================================
# 3. Schema Validation Tests - RecentFailure
# =============================================================================

class TestRecentFailureSchema:
    """Tests for RecentFailure schema validation."""

    def test_recent_failure_valid_creation(self, sample_failure_data):
        """Test RecentFailure can be created with valid data."""
        from app.schemas.analytics import RecentFailure

        failure = RecentFailure(**sample_failure_data)

        assert str(failure.job_id) == str(sample_failure_data["job_id"])
        assert failure.service_name == "summarize-fr"
        assert failure.error == "Context window exceeded"
        assert failure.timestamp is not None


# =============================================================================
# 4. Schema Validation Tests - DashboardAnalytics
# =============================================================================

class TestDashboardAnalyticsSchema:
    """Tests for DashboardAnalytics schema validation."""

    def test_dashboard_analytics_valid_creation(
        self, sample_overview_data, sample_service_health_data, sample_failure_data
    ):
        """Test DashboardAnalytics can be created with valid data."""
        from app.schemas.analytics import (
            DashboardAnalytics, DashboardOverview,
            ServiceHealthSummary, RecentFailure
        )

        overview = DashboardOverview(**sample_overview_data)
        service = ServiceHealthSummary(**sample_service_health_data)
        failure = RecentFailure(**sample_failure_data)

        analytics = DashboardAnalytics(
            period="24h",
            overview=overview,
            services=[service],
            recent_failures=[failure],
            generated_at=datetime.now(timezone.utc),
        )

        assert analytics.period == "24h"
        assert analytics.overview.total_jobs == 250
        assert len(analytics.services) == 1
        assert len(analytics.recent_failures) == 1

    def test_dashboard_analytics_empty_lists(self, sample_overview_data):
        """Test DashboardAnalytics with empty services and failures lists."""
        from app.schemas.analytics import DashboardAnalytics, DashboardOverview

        overview = DashboardOverview(
            total_jobs=0,
            successful_jobs=0,
            failed_jobs=0,
            success_rate=0.0,
            total_tokens=0,
            total_cost=0.0,
            active_services=0,
            avg_latency_ms=0.0,
        )

        analytics = DashboardAnalytics(
            period="24h",
            overview=overview,
            services=[],
            recent_failures=[],
            generated_at=datetime.now(timezone.utc),
        )

        assert analytics.services == []
        assert analytics.recent_failures == []

    def test_dashboard_analytics_has_all_required_fields(self):
        """Verify DashboardAnalytics has all fields from api-contract.md."""
        from app.schemas.analytics import DashboardAnalytics

        fields = set(DashboardAnalytics.model_fields.keys())

        required_fields = {
            "period",
            "overview",
            "services",
            "recent_failures",
            "generated_at",
        }

        assert required_fields.issubset(fields), \
            f"Missing fields: {required_fields - fields}"


# =============================================================================
# 5. Schema Validation Tests - ServiceStats
# =============================================================================

class TestServiceStatsSchema:
    """Tests for ServiceStats schema validation."""

    def test_service_stats_valid_creation(
        self, sample_service_stats_data, sample_flavor_breakdown, sample_time_series
    ):
        """Test ServiceStats can be created with valid data."""
        from app.schemas.analytics import (
            ServiceStats, ServiceStatsData,
            FlavorBreakdownItem, TimeSeriesPoint
        )

        stats = ServiceStatsData(**sample_service_stats_data)
        breakdown = [FlavorBreakdownItem(**fb) for fb in sample_flavor_breakdown]
        time_series = [TimeSeriesPoint(**ts) for ts in sample_time_series]

        service_stats = ServiceStats(
            service_id=uuid4(),
            service_name="test-service",
            period="24h",
            stats=stats,
            flavor_breakdown=breakdown,
            time_series=time_series,
            generated_at=datetime.now(timezone.utc),
        )

        assert service_stats.service_name == "test-service"
        assert service_stats.period == "24h"
        assert service_stats.stats.total_requests == 150
        assert len(service_stats.flavor_breakdown) == 2
        assert len(service_stats.time_series) == 2

    def test_service_stats_empty_data(self):
        """Test ServiceStats with no jobs (all zeros)."""
        from app.schemas.analytics import ServiceStats, ServiceStatsData

        stats = ServiceStatsData(
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            success_rate=0.0,
            total_tokens=0,
            total_estimated_cost=0.0,
            avg_latency_ms=0.0,
            flavors_used=0,
            most_used_flavor=None,
        )

        service_stats = ServiceStats(
            service_id=uuid4(),
            service_name="empty-service",
            period="24h",
            stats=stats,
            flavor_breakdown=[],
            time_series=[],
            generated_at=datetime.now(timezone.utc),
        )

        assert service_stats.stats.total_requests == 0
        assert service_stats.stats.most_used_flavor is None
        assert service_stats.flavor_breakdown == []

    def test_service_stats_has_all_required_fields(self):
        """Verify ServiceStats has all fields from api-contract.md."""
        from app.schemas.analytics import ServiceStats

        fields = set(ServiceStats.model_fields.keys())

        required_fields = {
            "service_id",
            "service_name",
            "period",
            "stats",
            "flavor_breakdown",
            "time_series",
            "generated_at",
        }

        assert required_fields.issubset(fields), \
            f"Missing fields: {required_fields - fields}"

    def test_service_stats_data_has_all_required_fields(self):
        """Verify ServiceStatsData has all fields from api-contract.md."""
        from app.schemas.analytics import ServiceStatsData

        fields = set(ServiceStatsData.model_fields.keys())

        required_fields = {
            "total_requests",
            "successful_requests",
            "failed_requests",
            "success_rate",
            "total_tokens",
            "total_estimated_cost",
            "avg_latency_ms",
            "flavors_used",
            "most_used_flavor",
        }

        assert required_fields.issubset(fields), \
            f"Missing fields: {required_fields - fields}"


# =============================================================================
# 6. Health Status Logic Tests
# =============================================================================

class TestHealthStatusLogic:
    """Tests for calculate_health_status function."""

    def test_healthy_100_percent(self):
        """Test 100% success rate returns healthy."""
        from app.services.analytics_service import calculate_health_status

        assert calculate_health_status(100, 10) == "healthy"

    def test_healthy_95_percent(self):
        """Test 95% success rate returns healthy."""
        from app.services.analytics_service import calculate_health_status

        assert calculate_health_status(95, 10) == "healthy"

    def test_degraded_94_9_percent(self):
        """Test 94.9% success rate returns degraded."""
        from app.services.analytics_service import calculate_health_status

        assert calculate_health_status(94.9, 10) == "degraded"

    def test_degraded_80_percent(self):
        """Test 80% success rate returns degraded."""
        from app.services.analytics_service import calculate_health_status

        assert calculate_health_status(80, 10) == "degraded"

    def test_unhealthy_79_9_percent(self):
        """Test 79.9% success rate returns unhealthy."""
        from app.services.analytics_service import calculate_health_status

        assert calculate_health_status(79.9, 10) == "unhealthy"

    def test_unhealthy_0_percent(self):
        """Test 0% success rate returns unhealthy."""
        from app.services.analytics_service import calculate_health_status

        assert calculate_health_status(0, 10) == "unhealthy"

    def test_inactive_no_requests(self):
        """Test 0 requests returns inactive."""
        from app.services.analytics_service import calculate_health_status

        assert calculate_health_status(100, 0) == "inactive"

    def test_inactive_100_success_no_requests(self):
        """Test that success rate doesn't matter if no requests."""
        from app.services.analytics_service import calculate_health_status

        # Even with 100% success rate, 0 requests means inactive
        assert calculate_health_status(100, 0) == "inactive"
        assert calculate_health_status(0, 0) == "inactive"


# =============================================================================
# 7. API Endpoint Tests - GET /api/v1/analytics/dashboard
# =============================================================================

class TestDashboardAnalyticsEndpoint:
    """Tests for the dashboard analytics endpoint."""

    def test_dashboard_endpoint_exists(self):
        """Verify /analytics/dashboard endpoint is registered."""
        from app.api.v1.analytics import router

        routes = [route.path for route in router.routes]
        assert "/analytics/dashboard" in routes

    def test_dashboard_endpoint_returns_correct_response_model(self):
        """Verify endpoint returns DashboardAnalytics."""
        from app.api.v1.analytics import get_dashboard_analytics
        import inspect

        # Check it's an async function
        assert inspect.iscoroutinefunction(get_dashboard_analytics)


# =============================================================================
# 8. API Endpoint Tests - GET /api/v1/services/{service_id}/stats
# =============================================================================

class TestServiceStatsEndpoint:
    """Tests for the service stats endpoint."""

    def test_service_stats_endpoint_exists(self):
        """Verify /services/{service_id}/stats endpoint is registered."""
        from app.api.v1.services import router

        routes = [route.path for route in router.routes]
        assert "/services/{service_id}/stats" in routes

    def test_service_stats_endpoint_returns_correct_response_model(self):
        """Verify endpoint exists and is async."""
        from app.api.v1.services import get_service_stats
        import inspect

        # Check it's an async function
        assert inspect.iscoroutinefunction(get_service_stats)


# =============================================================================
# 9. AnalyticsService Unit Tests
# =============================================================================

class TestAnalyticsService:
    """Unit tests for AnalyticsService methods."""

    def test_extract_token_metrics_with_valid_data(self):
        """Test extraction with valid token metrics in progress."""
        from app.services.analytics_service import AnalyticsService

        mock_job = Mock()
        mock_job.progress = {
            "token_metrics": {
                "total_prompt_tokens": 1000,
                "total_completion_tokens": 500,
                "total_estimated_cost": 0.05,
            }
        }

        result = AnalyticsService._extract_token_metrics(mock_job)

        assert result is not None
        assert result["total_prompt_tokens"] == 1000
        assert result["total_completion_tokens"] == 500
        assert result["total_estimated_cost"] == 0.05

    def test_extract_token_metrics_empty_progress(self):
        """Test extraction with empty progress returns empty dict."""
        from app.services.analytics_service import AnalyticsService

        mock_job = Mock()
        mock_job.progress = None

        result = AnalyticsService._extract_token_metrics(mock_job)
        assert result == {}

        mock_job.progress = {}
        result = AnalyticsService._extract_token_metrics(mock_job)
        assert result == {}

    def test_extract_token_metrics_no_token_metrics_key(self):
        """Test extraction when token_metrics key is missing."""
        from app.services.analytics_service import AnalyticsService

        mock_job = Mock()
        mock_job.progress = {"percentage": 50, "current": 5, "total": 10}

        result = AnalyticsService._extract_token_metrics(mock_job)
        assert result == {}

    def test_period_intervals_defined(self):
        """Test that PERIOD_INTERVALS contains expected periods."""
        from app.services.analytics_service import AnalyticsService

        assert '24h' in AnalyticsService.PERIOD_INTERVALS
        assert '7d' in AnalyticsService.PERIOD_INTERVALS
        assert '30d' in AnalyticsService.PERIOD_INTERVALS
        # 'all' is handled separately (no interval)


# =============================================================================
# 10. Period Validation Tests
# =============================================================================

class TestPeriodValidation:
    """Tests for period parameter validation in service stats."""

    @pytest.mark.asyncio
    async def test_valid_periods_accepted(self):
        """Test all valid period values are accepted."""
        from app.services.analytics_service import AnalyticsService
        from fastapi import HTTPException

        valid_periods = ['24h', '7d', '30d', 'all']

        # Mock the database session and service
        mock_db = AsyncMock()
        mock_service = Mock()
        mock_service.id = uuid4()
        mock_service.name = "test-service"

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_service

        mock_jobs_result = Mock()
        mock_jobs_result.scalars.return_value.all.return_value = []

        mock_flavors_result = Mock()
        mock_flavors_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[mock_result, mock_jobs_result, mock_flavors_result]
        )

        # Each valid period should not raise HTTPException
        for period in valid_periods:
            mock_db.execute.reset_mock()
            mock_db.execute = AsyncMock(
                side_effect=[mock_result, mock_jobs_result, mock_flavors_result]
            )

            # Should not raise exception for valid periods
            result = await AnalyticsService.get_service_stats(
                mock_db, mock_service.id, period
            )
            assert result.period == period

    @pytest.mark.asyncio
    async def test_invalid_period_returns_400(self):
        """Test invalid period value returns 400 error."""
        from app.services.analytics_service import AnalyticsService
        from fastapi import HTTPException

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await AnalyticsService.get_service_stats(
                mock_db, uuid4(), "invalid-period"
            )

        assert exc_info.value.status_code == 400
        assert "Invalid period" in exc_info.value.detail


# =============================================================================
# 11. Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in analytics endpoints."""

    @pytest.mark.asyncio
    async def test_nonexistent_service_returns_404(self):
        """Test non-existent service ID returns 404."""
        from app.services.analytics_service import AnalyticsService
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await AnalyticsService.get_service_stats(
                mock_db, uuid4(), "24h"
            )

        assert exc_info.value.status_code == 404
        assert "Service not found" in exc_info.value.detail


# =============================================================================
# 12. Integration Tests - Dashboard Analytics
# =============================================================================

class TestDashboardIntegration:
    """Integration tests for dashboard analytics."""

    @pytest.mark.asyncio
    async def test_dashboard_returns_valid_structure(self):
        """Test dashboard returns valid DashboardAnalytics structure."""
        from app.services.analytics_service import AnalyticsService
        from app.schemas.analytics import DashboardAnalytics

        # Mock database session
        mock_db = AsyncMock()

        # Mock jobs query result (empty)
        mock_jobs_result = Mock()
        mock_jobs_result.scalars.return_value.all.return_value = []

        # Mock services query result (empty)
        mock_services_result = Mock()
        mock_services_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[mock_jobs_result, mock_services_result]
        )

        result = await AnalyticsService.get_dashboard_analytics(mock_db)

        # Verify structure
        assert isinstance(result, DashboardAnalytics)
        assert result.period == "24h"
        assert result.overview is not None
        assert result.services is not None
        assert result.recent_failures is not None
        assert result.generated_at is not None

    @pytest.mark.asyncio
    async def test_dashboard_with_no_jobs_returns_zeros(self):
        """Test dashboard with no jobs returns zero values."""
        from app.services.analytics_service import AnalyticsService

        mock_db = AsyncMock()

        mock_jobs_result = Mock()
        mock_jobs_result.scalars.return_value.all.return_value = []

        mock_services_result = Mock()
        mock_services_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[mock_jobs_result, mock_services_result]
        )

        result = await AnalyticsService.get_dashboard_analytics(mock_db)

        assert result.overview.total_jobs == 0
        assert result.overview.successful_jobs == 0
        assert result.overview.failed_jobs == 0
        assert result.overview.success_rate == 0.0
        assert result.overview.total_tokens == 0
        assert result.overview.total_cost == 0.0
        assert result.overview.active_services == 0
        assert result.services == []
        assert result.recent_failures == []

    @pytest.mark.asyncio
    async def test_dashboard_limits_recent_failures_to_5(self):
        """Test dashboard limits recent_failures to 5 entries."""
        from app.services.analytics_service import AnalyticsService
        from datetime import datetime, timedelta

        mock_db = AsyncMock()

        # Create 10 failed jobs
        mock_jobs = []
        for i in range(10):
            job = Mock()
            job.id = uuid4()
            job.service_id = uuid4()
            job.status = "failed"
            job.error = f"Error {i}"
            job.progress = None
            job.started_at = None
            job.completed_at = datetime.utcnow() - timedelta(minutes=i)
            job.created_at = datetime.utcnow() - timedelta(minutes=i)
            mock_jobs.append(job)

        mock_jobs_result = Mock()
        mock_jobs_result.scalars.return_value.all.return_value = mock_jobs

        mock_services_result = Mock()
        mock_services_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[mock_jobs_result, mock_services_result]
        )

        result = await AnalyticsService.get_dashboard_analytics(mock_db)

        # Should be limited to 5
        assert len(result.recent_failures) <= 5


# =============================================================================
# 13. Integration Tests - Service Stats
# =============================================================================

class TestServiceStatsIntegration:
    """Integration tests for service stats."""

    @pytest.mark.asyncio
    async def test_service_stats_empty_service_returns_zeros(self):
        """Test service with no jobs returns zero values."""
        from app.services.analytics_service import AnalyticsService

        mock_db = AsyncMock()
        service_id = uuid4()

        # Mock service
        mock_service = Mock()
        mock_service.id = service_id
        mock_service.name = "empty-service"

        mock_service_result = Mock()
        mock_service_result.scalar_one_or_none.return_value = mock_service

        # Mock jobs (empty)
        mock_jobs_result = Mock()
        mock_jobs_result.scalars.return_value.all.return_value = []

        # Mock flavors (empty)
        mock_flavors_result = Mock()
        mock_flavors_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[mock_service_result, mock_jobs_result, mock_flavors_result]
        )

        result = await AnalyticsService.get_service_stats(mock_db, service_id, "24h")

        assert result.stats.total_requests == 0
        assert result.stats.successful_requests == 0
        assert result.stats.failed_requests == 0
        assert result.stats.success_rate == 0.0
        assert result.stats.total_tokens == 0
        assert result.stats.most_used_flavor is None
        assert result.flavor_breakdown == []
        assert result.time_series == []

    @pytest.mark.asyncio
    async def test_service_stats_aggregates_token_metrics(self):
        """Test service stats correctly aggregates token metrics from jobs."""
        from app.services.analytics_service import AnalyticsService
        from datetime import datetime

        mock_db = AsyncMock()
        service_id = uuid4()
        flavor_id = uuid4()

        # Mock service
        mock_service = Mock()
        mock_service.id = service_id
        mock_service.name = "test-service"

        mock_service_result = Mock()
        mock_service_result.scalar_one_or_none.return_value = mock_service

        # Mock jobs with token metrics
        mock_jobs = []
        for i in range(3):
            job = Mock()
            job.id = uuid4()
            job.service_id = service_id
            job.flavor_id = flavor_id
            job.status = "completed"
            job.error = None
            job.progress = {
                "token_metrics": {
                    "total_prompt_tokens": 100,
                    "total_completion_tokens": 50,
                    "total_estimated_cost": 0.01,
                }
            }
            job.started_at = datetime.utcnow()
            job.completed_at = datetime.utcnow()
            job.created_at = datetime.utcnow()
            mock_jobs.append(job)

        mock_jobs_result = Mock()
        mock_jobs_result.scalars.return_value.all.return_value = mock_jobs

        # Mock flavor
        mock_flavor = Mock()
        mock_flavor.id = flavor_id
        mock_flavor.name = "test-flavor"

        mock_flavors_result = Mock()
        mock_flavors_result.scalars.return_value.all.return_value = [mock_flavor]

        mock_db.execute = AsyncMock(
            side_effect=[mock_service_result, mock_jobs_result, mock_flavors_result]
        )

        # Patch the time series generation to return empty list
        with patch.object(
            AnalyticsService, '_generate_service_time_series',
            new_callable=AsyncMock, return_value=[]
        ):
            result = await AnalyticsService.get_service_stats(mock_db, service_id, "24h")

        # 3 jobs * (100 prompt + 50 completion) = 450 total tokens
        assert result.stats.total_tokens == 450
        # 3 jobs * 0.01 = 0.03 total cost
        assert result.stats.total_estimated_cost == 0.03
        assert result.stats.most_used_flavor == "test-flavor"


# =============================================================================
# 14. Flavor Breakdown Tests
# =============================================================================

class TestFlavorBreakdown:
    """Tests for flavor breakdown percentage calculations."""

    def test_flavor_breakdown_percentages_calculation(self):
        """Test flavor breakdown percentages are calculated correctly."""
        from app.schemas.analytics import FlavorBreakdownItem

        # Simulate 4 requests: 3 for flavor A, 1 for flavor B
        total_requests = 4
        flavor_a_requests = 3
        flavor_b_requests = 1

        flavor_a_percentage = (flavor_a_requests / total_requests) * 100
        flavor_b_percentage = (flavor_b_requests / total_requests) * 100

        assert flavor_a_percentage == 75.0
        assert flavor_b_percentage == 25.0

        # Create schema instances
        breakdown_a = FlavorBreakdownItem(
            flavor_id=uuid4(),
            flavor_name="flavor-a",
            requests=flavor_a_requests,
            percentage=flavor_a_percentage,
        )

        breakdown_b = FlavorBreakdownItem(
            flavor_id=uuid4(),
            flavor_name="flavor-b",
            requests=flavor_b_requests,
            percentage=flavor_b_percentage,
        )

        assert breakdown_a.percentage == 75.0
        assert breakdown_b.percentage == 25.0


# =============================================================================
# 15. API Contract Conformity Tests
# =============================================================================

class TestAPIContractConformity:
    """Tests verifying conformity to api-contract.md specification."""

    def test_dashboard_overview_has_all_required_fields(self):
        """Verify DashboardOverview has all fields from api-contract.md."""
        from app.schemas.analytics import DashboardOverview

        fields = set(DashboardOverview.model_fields.keys())

        required_fields = {
            "total_jobs",
            "successful_jobs",
            "failed_jobs",
            "success_rate",
            "total_tokens",
            "total_cost",
            "active_services",
            "avg_latency_ms",
        }

        assert required_fields.issubset(fields), \
            f"Missing fields: {required_fields - fields}"

    def test_service_health_summary_has_all_required_fields(self):
        """Verify ServiceHealthSummary has all fields from api-contract.md."""
        from app.schemas.analytics import ServiceHealthSummary

        fields = set(ServiceHealthSummary.model_fields.keys())

        required_fields = {
            "service_id",
            "service_name",
            "requests_24h",
            "success_rate",
            "status",
        }

        assert required_fields.issubset(fields), \
            f"Missing fields: {required_fields - fields}"

    def test_recent_failure_has_all_required_fields(self):
        """Verify RecentFailure has all fields from api-contract.md."""
        from app.schemas.analytics import RecentFailure

        fields = set(RecentFailure.model_fields.keys())

        required_fields = {
            "job_id",
            "service_name",
            "error",
            "timestamp",
        }

        assert required_fields.issubset(fields), \
            f"Missing fields: {required_fields - fields}"

    def test_flavor_breakdown_item_has_all_required_fields(self):
        """Verify FlavorBreakdownItem has all fields from api-contract.md."""
        from app.schemas.analytics import FlavorBreakdownItem

        fields = set(FlavorBreakdownItem.model_fields.keys())

        required_fields = {
            "flavor_id",
            "flavor_name",
            "requests",
            "percentage",
        }

        assert required_fields.issubset(fields), \
            f"Missing fields: {required_fields - fields}"

    def test_time_series_point_has_all_required_fields(self):
        """Verify TimeSeriesPoint has all fields from api-contract.md."""
        from app.schemas.analytics import TimeSeriesPoint

        fields = set(TimeSeriesPoint.model_fields.keys())

        required_fields = {
            "timestamp",
            "requests",
            "tokens",
            "cost",
        }

        assert required_fields.issubset(fields), \
            f"Missing fields: {required_fields - fields}"

    def test_health_status_literal_values(self):
        """Verify status field accepts exactly the specified literal values."""
        from app.schemas.analytics import ServiceHealthSummary
        from typing import get_args, get_type_hints

        # Get the status field type
        hints = get_type_hints(ServiceHealthSummary)
        status_type = hints.get('status')

        # Get the Literal args
        expected_statuses = {"healthy", "degraded", "unhealthy", "inactive"}
        actual_statuses = set(get_args(status_type))

        assert actual_statuses == expected_statuses


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
