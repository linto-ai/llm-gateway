#!/usr/bin/env python3
"""Service for system-wide analytics and service-level statistics.

Provides dashboard health overview and service-level statistics
by aggregating data from the jobs table.
"""

from typing import List
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from fastapi import HTTPException, status

from app.models.job import Job
from app.models.service import Service
from app.models.service_flavor import ServiceFlavor
from app.schemas.analytics import (
    DashboardAnalytics,
    DashboardOverview,
    ServiceHealthSummary,
    RecentFailure,
    ServiceStats,
    ServiceStatsData,
    FlavorBreakdownItem,
    TimeSeriesPoint,
)


def calculate_health_status(success_rate: float, total_requests: int) -> str:
    """
    Calculate health status based on success rate and request count.

    - healthy: success_rate >= 95%
    - degraded: success_rate >= 80% and < 95%
    - unhealthy: success_rate < 80%
    - inactive: no requests in period
    """
    if total_requests == 0:
        return "inactive"
    if success_rate >= 95:
        return "healthy"
    if success_rate >= 80:
        return "degraded"
    return "unhealthy"


class AnalyticsService:
    """Service for system-wide analytics and statistics.

    Aggregates metrics from completed jobs for dashboard and service-level views.
    """

    PERIOD_INTERVALS = {
        '24h': timedelta(hours=24),
        '7d': timedelta(days=7),
        '30d': timedelta(days=30),
    }

    @staticmethod
    def _extract_token_metrics(job: Job) -> dict:
        """Extract token metrics from job.progress."""
        if not job.progress:
            return {}
        return job.progress.get("token_metrics", {})

    @staticmethod
    async def get_dashboard_analytics(db: AsyncSession) -> DashboardAnalytics:
        """
        Get system-wide health overview for the last 24 hours.

        Returns:
            DashboardAnalytics: Dashboard data with overview, service health, and recent failures
        """
        now = datetime.utcnow()
        start_time = now - timedelta(hours=24)

        # Get all jobs from last 24h
        result = await db.execute(
            select(Job)
            .where(Job.created_at >= start_time)
            .order_by(Job.created_at.desc())
        )
        jobs = result.scalars().all()

        # Get all active services
        services_result = await db.execute(
            select(Service).where(Service.is_active)
        )
        services = services_result.scalars().all()

        # Calculate overview metrics
        total_jobs = len(jobs)
        successful_jobs = sum(1 for j in jobs if j.status == "completed")
        failed_jobs = sum(1 for j in jobs if j.status == "failed")
        success_rate = (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0.0

        # Aggregate token and cost metrics
        total_tokens = 0
        total_cost = 0.0
        latencies = []

        for job in jobs:
            metrics = AnalyticsService._extract_token_metrics(job)
            if metrics:
                total_tokens += metrics.get("total_prompt_tokens", 0)
                total_tokens += metrics.get("total_completion_tokens", 0)
                cost = metrics.get("total_estimated_cost")
                if cost is not None:
                    total_cost += cost

            if job.started_at and job.completed_at:
                latency_ms = int((job.completed_at - job.started_at).total_seconds() * 1000)
                if latency_ms >= 0:  # Skip invalid negative latencies (orphaned/cancelled jobs)
                    latencies.append(latency_ms)

        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        # Count active services (services with at least one job in period)
        active_service_ids = set(j.service_id for j in jobs)
        active_services_count = len(active_service_ids)

        overview = DashboardOverview(
            total_jobs=total_jobs,
            successful_jobs=successful_jobs,
            failed_jobs=failed_jobs,
            success_rate=round(success_rate, 1),
            total_tokens=total_tokens,
            total_cost=round(total_cost, 2),
            active_services=active_services_count,
            avg_latency_ms=round(avg_latency, 0),
        )

        # Build per-service health summaries
        service_summaries = []
        for service in services:
            service_jobs = [j for j in jobs if j.service_id == service.id]
            service_total = len(service_jobs)
            service_successful = sum(1 for j in service_jobs if j.status == "completed")
            service_success_rate = (service_successful / service_total * 100) if service_total > 0 else 0.0

            health_status = calculate_health_status(service_success_rate, service_total)

            service_summaries.append(
                ServiceHealthSummary(
                    service_id=service.id,
                    service_name=service.name,
                    requests_24h=service_total,
                    success_rate=round(service_success_rate, 1),
                    status=health_status,
                )
            )

        # Get 5 most recent failures
        failed_jobs_list = [j for j in jobs if j.status == "failed"]
        recent_failures = []

        # Build service name lookup
        service_name_lookup = {s.id: s.name for s in services}

        for job in failed_jobs_list[:5]:
            service_name = service_name_lookup.get(job.service_id, "Unknown Service")
            error_msg = job.error or "Unknown error"

            recent_failures.append(
                RecentFailure(
                    job_id=job.id,
                    service_name=service_name,
                    error=error_msg[:200],  # Truncate long errors
                    timestamp=job.completed_at or job.created_at,
                )
            )

        return DashboardAnalytics(
            period="24h",
            overview=overview,
            services=service_summaries,
            recent_failures=recent_failures,
            generated_at=now,
        )

    @staticmethod
    async def get_service_stats(
        db: AsyncSession,
        service_id: UUID,
        period: str = "24h"
    ) -> ServiceStats:
        """
        Get aggregated statistics for a service across all flavors.

        Args:
            db: Database session
            service_id: ID of the service
            period: Time period ('24h', '7d', '30d', 'all')

        Returns:
            ServiceStats: Comprehensive service statistics

        Raises:
            HTTPException: If service not found or invalid period
        """
        # Validate period
        if period not in ['24h', '7d', '30d', 'all']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid period. Must be one of: 24h, 7d, 30d, all"
            )

        # Get service
        result = await db.execute(
            select(Service).where(Service.id == service_id)
        )
        service = result.scalar_one_or_none()
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )

        now = datetime.utcnow()

        # Build time filter
        filters = [Job.service_id == service_id]
        if period != 'all':
            start_time = now - AnalyticsService.PERIOD_INTERVALS[period]
            filters.append(Job.created_at >= start_time)

        # Get all jobs for this service in the period
        result = await db.execute(
            select(Job).where(and_(*filters)).order_by(Job.created_at.desc())
        )
        jobs = result.scalars().all()

        # Get all flavors for this service
        flavors_result = await db.execute(
            select(ServiceFlavor).where(ServiceFlavor.service_id == service_id)
        )
        flavors = flavors_result.scalars().all()
        flavor_lookup = {f.id: f for f in flavors}

        # Empty data case
        if not jobs:
            return ServiceStats(
                service_id=service.id,
                service_name=service.name,
                period=period,
                stats=ServiceStatsData(
                    total_requests=0,
                    successful_requests=0,
                    failed_requests=0,
                    success_rate=0.0,
                    total_tokens=0,
                    total_estimated_cost=0.0,
                    avg_latency_ms=0.0,
                    flavors_used=0,
                    most_used_flavor=None,
                ),
                flavor_breakdown=[],
                time_series=[],
                generated_at=now,
            )

        # Aggregate metrics
        total_requests = len(jobs)
        successful_requests = sum(1 for j in jobs if j.status == "completed")
        failed_requests = sum(1 for j in jobs if j.status == "failed")
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0.0

        total_tokens = 0
        total_cost = 0.0
        latencies = []

        # Count requests per flavor
        flavor_request_counts = {}

        for job in jobs:
            # Extract token metrics
            metrics = AnalyticsService._extract_token_metrics(job)
            if metrics:
                total_tokens += metrics.get("total_prompt_tokens", 0)
                total_tokens += metrics.get("total_completion_tokens", 0)
                cost = metrics.get("total_estimated_cost")
                if cost is not None:
                    total_cost += cost

            # Calculate latency
            if job.started_at and job.completed_at:
                latency_ms = int((job.completed_at - job.started_at).total_seconds() * 1000)
                if latency_ms >= 0:  # Skip invalid negative latencies (orphaned/cancelled jobs)
                    latencies.append(latency_ms)

            # Count flavor usage
            if job.flavor_id:
                flavor_request_counts[job.flavor_id] = flavor_request_counts.get(job.flavor_id, 0) + 1

        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        # Determine most used flavor
        flavors_used = len(flavor_request_counts)
        most_used_flavor = None
        if flavor_request_counts:
            most_used_id = max(flavor_request_counts, key=flavor_request_counts.get)
            most_used_f = flavor_lookup.get(most_used_id)
            if most_used_f:
                most_used_flavor = most_used_f.name

        stats = ServiceStatsData(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            success_rate=round(success_rate, 1),
            total_tokens=total_tokens,
            total_estimated_cost=round(total_cost, 2),
            avg_latency_ms=round(avg_latency, 0),
            flavors_used=flavors_used,
            most_used_flavor=most_used_flavor,
        )

        # Build flavor breakdown
        flavor_breakdown = []
        for flavor_id, request_count in sorted(
            flavor_request_counts.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            flavor = flavor_lookup.get(flavor_id)
            if flavor:
                percentage = (request_count / total_requests * 100) if total_requests > 0 else 0.0
                flavor_breakdown.append(
                    FlavorBreakdownItem(
                        flavor_id=flavor.id,
                        flavor_name=flavor.name,
                        requests=request_count,
                        percentage=round(percentage, 1),
                    )
                )

        # Generate time series
        time_series = await AnalyticsService._generate_service_time_series(
            db, service_id, period
        )

        return ServiceStats(
            service_id=service.id,
            service_name=service.name,
            period=period,
            stats=stats,
            flavor_breakdown=flavor_breakdown,
            time_series=time_series,
            generated_at=now,
        )

    @staticmethod
    async def _generate_service_time_series(
        db: AsyncSession,
        service_id: UUID,
        period: str
    ) -> List[TimeSeriesPoint]:
        """
        Generate time series data for a service.

        Uses hourly buckets for 24h, daily buckets for 7d/30d/all.
        """
        # Determine bucket size
        if period == '24h':
            trunc = 'hour'
        else:
            trunc = 'day'

        # Build filters
        filters = [Job.service_id == service_id]
        if period != 'all':
            start_time = datetime.utcnow() - AnalyticsService.PERIOD_INTERVALS[period]
            filters.append(Job.created_at >= start_time)

        # Query jobs grouped by time bucket
        result = await db.execute(
            select(
                func.date_trunc(trunc, Job.created_at).label('bucket'),
                func.count(Job.id).label('requests'),
            )
            .where(and_(*filters))
            .group_by(text('bucket'))
            .order_by(text('bucket'))
        )

        buckets = result.all()

        # For each bucket, aggregate token/cost data
        time_series = []
        for row in buckets:
            bucket_time = row.bucket

            # Get jobs in this bucket
            bucket_filters = filters.copy()
            bucket_filters.append(func.date_trunc(trunc, Job.created_at) == bucket_time)

            jobs_result = await db.execute(
                select(Job).where(and_(*bucket_filters))
            )
            bucket_jobs = jobs_result.scalars().all()

            # Aggregate tokens and cost
            total_tokens = 0
            total_cost = 0.0
            for job in bucket_jobs:
                metrics = AnalyticsService._extract_token_metrics(job)
                if metrics:
                    total_tokens += metrics.get("total_prompt_tokens", 0)
                    total_tokens += metrics.get("total_completion_tokens", 0)
                    cost = metrics.get("total_estimated_cost")
                    if cost:
                        total_cost += cost

            time_series.append(
                TimeSeriesPoint(
                    timestamp=bucket_time,
                    requests=row.requests,
                    tokens=total_tokens,
                    cost=round(total_cost, 2),
                )
            )

        return time_series


# Singleton instance
analytics_service = AnalyticsService()
