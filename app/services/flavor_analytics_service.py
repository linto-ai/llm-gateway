#!/usr/bin/env python3
"""Service for flavor usage analytics and statistics.

Queries jobs table for analytics. Token metrics are extracted from job.progress.token_metrics.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from fastapi import HTTPException, status
import statistics

from app.models.job import Job
from app.models.service_flavor import ServiceFlavor
from app.models.service import Service
from app.schemas.flavor_analytics import (
    FlavorStats,
    FlavorStatsData,
    ServiceFlavorComparison,
    FlavorComparison,
    ServiceFlavorComparisonTotals,
    TimeSeriesPoint,
    FlavorUsageHistory,
    FlavorUsageRecord
)


class FlavorAnalyticsService:
    """Service for flavor usage analytics and statistics.

    Aggregates metrics from completed jobs rather than a separate usage table.
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
    async def get_flavor_stats(
        db: AsyncSession,
        flavor_id: UUID,
        period: str = '24h'
    ) -> FlavorStats:
        """
        Get comprehensive statistics for a flavor from completed jobs.

        Args:
            db: Database session
            flavor_id: ID of the flavor
            period: Time period ('24h', '7d', '30d', 'all')

        Returns:
            FlavorStats: Comprehensive statistics
        """
        # Get flavor
        result = await db.execute(
            select(ServiceFlavor).where(ServiceFlavor.id == flavor_id)
        )
        flavor = result.scalar_one_or_none()
        if not flavor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flavor not found"
            )

        # Build time filter
        filters = [Job.flavor_id == flavor_id]
        if period != 'all':
            if period not in FlavorAnalyticsService.PERIOD_INTERVALS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid period. Must be one of: 24h, 7d, 30d, all"
                )
            start_time = datetime.utcnow() - FlavorAnalyticsService.PERIOD_INTERVALS[period]
            filters.append(Job.created_at >= start_time)

        # Get all jobs for this flavor in the period
        result = await db.execute(
            select(Job).where(and_(*filters)).order_by(Job.created_at.desc())
        )
        jobs = result.scalars().all()

        if not jobs:
            stats_data = FlavorStatsData(
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                success_rate=0.0,
                total_input_tokens=0,
                total_output_tokens=0,
                total_tokens=0,
                avg_input_tokens=0.0,
                avg_output_tokens=0.0,
                avg_latency_ms=0.0,
                min_latency_ms=0,
                max_latency_ms=0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                total_estimated_cost=0.0,
                avg_cost_per_request=0.0,
                time_series=[]
            )
            return FlavorStats(
                flavor_id=flavor.id,
                flavor_name=flavor.name,
                period=period,
                stats=stats_data,
                generated_at=datetime.utcnow()
            )

        # Aggregate metrics
        total_requests = len(jobs)
        successful_requests = sum(1 for j in jobs if j.status == "completed")
        failed_requests = sum(1 for j in jobs if j.status == "failed")
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0.0

        # Extract token metrics and latencies from jobs
        total_input = 0
        total_output = 0
        total_cost = 0.0
        latencies = []
        jobs_with_tokens = 0

        for job in jobs:
            metrics = FlavorAnalyticsService._extract_token_metrics(job)
            if metrics:
                input_tokens = metrics.get("total_prompt_tokens", 0)
                output_tokens = metrics.get("total_completion_tokens", 0)
                cost = metrics.get("total_estimated_cost")

                total_input += input_tokens
                total_output += output_tokens
                if cost is not None:
                    total_cost += cost
                jobs_with_tokens += 1

            # Calculate latency from started_at to completed_at
            if job.started_at and job.completed_at:
                latency_ms = int((job.completed_at - job.started_at).total_seconds() * 1000)
                latencies.append(latency_ms)

        total_tokens = total_input + total_output
        avg_input = total_input / jobs_with_tokens if jobs_with_tokens > 0 else 0.0
        avg_output = total_output / jobs_with_tokens if jobs_with_tokens > 0 else 0.0
        avg_cost = total_cost / successful_requests if successful_requests > 0 else 0.0

        # Latency stats
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        min_latency = min(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0
        p50 = FlavorAnalyticsService.calculate_percentile(sorted(latencies), 50) if latencies else 0.0
        p95 = FlavorAnalyticsService.calculate_percentile(sorted(latencies), 95) if latencies else 0.0
        p99 = FlavorAnalyticsService.calculate_percentile(sorted(latencies), 99) if latencies else 0.0

        # Generate time series
        time_series = await FlavorAnalyticsService.generate_time_series(db, flavor_id, period)

        stats_data = FlavorStatsData(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            success_rate=success_rate,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_tokens=total_tokens,
            avg_input_tokens=avg_input,
            avg_output_tokens=avg_output,
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            total_estimated_cost=total_cost,
            avg_cost_per_request=avg_cost,
            time_series=time_series
        )

        return FlavorStats(
            flavor_id=flavor.id,
            flavor_name=flavor.name,
            period=period,
            stats=stats_data,
            generated_at=datetime.utcnow()
        )

    @staticmethod
    async def compare_service_flavors(
        db: AsyncSession,
        service_id: UUID,
        period: str = '24h'
    ) -> ServiceFlavorComparison:
        """
        Compare all flavors for a service based on job data.

        Args:
            db: Database session
            service_id: ID of the service
            period: Time period ('24h', '7d', '30d', 'all')

        Returns:
            ServiceFlavorComparison: Comparison of all flavors
        """
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

        # Get all flavors for service
        result = await db.execute(
            select(ServiceFlavor).where(ServiceFlavor.service_id == service_id)
        )
        flavors = result.scalars().all()

        # Build time filter
        if period != 'all':
            if period not in FlavorAnalyticsService.PERIOD_INTERVALS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid period. Must be one of: 24h, 7d, 30d, all"
                )
            start_time = datetime.utcnow() - FlavorAnalyticsService.PERIOD_INTERVALS[period]
        else:
            start_time = None

        # Get total jobs for all flavors in this service
        total_filter = [Job.service_id == service_id]
        if start_time:
            total_filter.append(Job.created_at >= start_time)

        result = await db.execute(
            select(func.count(Job.id)).where(and_(*total_filter))
        )
        total_service_requests = result.scalar() or 0

        # Build comparison for each flavor
        flavor_comparisons = []
        total_tokens_sum = 0
        total_cost_sum = 0.0

        for flavor in flavors:
            # Get jobs for this flavor
            filters = [Job.flavor_id == flavor.id]
            if start_time:
                filters.append(Job.created_at >= start_time)

            result = await db.execute(
                select(Job).where(and_(*filters))
            )
            jobs = result.scalars().all()

            total_requests = len(jobs)
            successful_requests = sum(1 for j in jobs if j.status == "completed")
            success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0.0
            usage_percentage = (total_requests / total_service_requests * 100) if total_service_requests > 0 else 0.0

            # Aggregate tokens and cost
            total_tokens = 0
            total_cost = 0.0
            latencies = []

            for job in jobs:
                metrics = FlavorAnalyticsService._extract_token_metrics(job)
                if metrics:
                    total_tokens += metrics.get("total_prompt_tokens", 0) + metrics.get("total_completion_tokens", 0)
                    cost = metrics.get("total_estimated_cost")
                    if cost:
                        total_cost += cost

                if job.started_at and job.completed_at:
                    latency_ms = int((job.completed_at - job.started_at).total_seconds() * 1000)
                    latencies.append(latency_ms)

            avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

            total_tokens_sum += total_tokens
            total_cost_sum += total_cost

            flavor_comparisons.append(
                FlavorComparison(
                    flavor_id=flavor.id,
                    flavor_name=flavor.name,
                    is_default=flavor.is_default,
                    total_requests=total_requests,
                    success_rate=success_rate,
                    total_tokens=total_tokens,
                    avg_latency_ms=avg_latency,
                    total_estimated_cost=total_cost,
                    usage_percentage=usage_percentage
                )
            )

        return ServiceFlavorComparison(
            service_id=service.id,
            service_name=service.name,
            period=period,
            flavors=flavor_comparisons,
            totals=ServiceFlavorComparisonTotals(
                total_requests=total_service_requests,
                total_tokens=total_tokens_sum,
                total_cost=total_cost_sum
            ),
            generated_at=datetime.utcnow()
        )

    @staticmethod
    async def get_usage_history(
        db: AsyncSession,
        flavor_id: UUID,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> FlavorUsageHistory:
        """
        Get paginated usage history for a flavor from jobs.

        Args:
            db: Database session
            flavor_id: ID of the flavor
            limit: Max records to return
            offset: Pagination offset
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            FlavorUsageHistory: Paginated usage records
        """
        # Build filters
        filters = [Job.flavor_id == flavor_id]
        if start_date:
            filters.append(Job.created_at >= start_date)
        if end_date:
            filters.append(Job.created_at <= end_date)

        # Get total count
        result = await db.execute(
            select(func.count(Job.id)).where(and_(*filters))
        )
        total = result.scalar()

        # Get paginated jobs
        result = await db.execute(
            select(Job)
            .where(and_(*filters))
            .order_by(Job.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        jobs = result.scalars().all()

        # Convert to usage records
        items = []
        for job in jobs:
            metrics = FlavorAnalyticsService._extract_token_metrics(job)

            input_tokens = metrics.get("total_prompt_tokens", 0) if metrics else 0
            output_tokens = metrics.get("total_completion_tokens", 0) if metrics else 0
            total_tokens = input_tokens + output_tokens
            estimated_cost = metrics.get("total_estimated_cost") if metrics else None

            latency_ms = 0
            if job.started_at and job.completed_at:
                latency_ms = int((job.completed_at - job.started_at).total_seconds() * 1000)

            items.append(FlavorUsageRecord(
                id=job.id,
                flavor_id=job.flavor_id,
                job_id=job.id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                estimated_cost=estimated_cost,
                success=job.status == "completed",
                error_message=job.error,
                executed_at=job.completed_at or job.created_at
            ))

        return FlavorUsageHistory(total=total, items=items)

    @staticmethod
    def calculate_percentile(values: List[int], percentile: int) -> float:
        """
        Calculate percentile from sorted list of values.
        """
        if not values:
            return 0.0
        if len(values) == 1:
            return float(values[0])
        return statistics.quantiles(values, n=100)[percentile - 1]

    @staticmethod
    async def generate_time_series(
        db: AsyncSession,
        flavor_id: UUID,
        period: str
    ) -> List[TimeSeriesPoint]:
        """
        Generate time series data for a flavor from jobs.
        """
        # Determine bucket size
        if period == '24h':
            trunc = 'hour'
        else:
            trunc = 'day'

        # Build filters
        filters = [Job.flavor_id == flavor_id]
        if period != 'all':
            start_time = datetime.utcnow() - FlavorAnalyticsService.PERIOD_INTERVALS[period]
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

        # For each bucket, we need to get token/cost data from jobs
        # Since we can't aggregate JSONB easily in SQL, we'll fetch jobs per bucket
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
                metrics = FlavorAnalyticsService._extract_token_metrics(job)
                if metrics:
                    total_tokens += metrics.get("total_prompt_tokens", 0) + metrics.get("total_completion_tokens", 0)
                    cost = metrics.get("total_estimated_cost")
                    if cost:
                        total_cost += cost

            time_series.append(
                TimeSeriesPoint(
                    timestamp=bucket_time,
                    requests=row.requests,
                    tokens=total_tokens,
                    cost=total_cost
                )
            )

        return time_series
