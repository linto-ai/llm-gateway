#!/usr/bin/env python3
"""Service for tracking flavor usage and cost analytics."""

from typing import Optional
from uuid import UUID
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.flavor_usage import FlavorUsage
from app.models.service_flavor import ServiceFlavor


class FlavorUsageTracker:
    """Track flavor usage for analytics and cost monitoring."""

    @staticmethod
    async def record_usage(
        db: AsyncSession,
        flavor_id: UUID,
        job_id: Optional[UUID],
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> FlavorUsage:
        """
        Record a flavor execution for analytics.

        Args:
            db: Database session
            flavor_id: ID of the flavor used
            job_id: Optional job ID (None for test executions)
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            latency_ms: Execution latency in milliseconds
            success: Whether execution succeeded
            error_message: Error message if execution failed

        Returns:
            FlavorUsage: Created usage record
        """
        # Calculate total tokens
        total_tokens = input_tokens + output_tokens

        # Get flavor to retrieve estimated_cost_per_1k_tokens
        result = await db.execute(
            select(ServiceFlavor).where(ServiceFlavor.id == flavor_id)
        )
        flavor = result.scalar_one_or_none()

        # Calculate estimated cost
        estimated_cost = None
        if flavor and flavor.estimated_cost_per_1k_tokens is not None:
            estimated_cost = (total_tokens / 1000.0) * flavor.estimated_cost_per_1k_tokens

        # Create FlavorUsage record
        usage_record = FlavorUsage(
            id=uuid.uuid4(),
            flavor_id=flavor_id,
            job_id=job_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            estimated_cost=estimated_cost,
            success=success,
            error_message=error_message
        )

        db.add(usage_record)
        await db.commit()
        await db.refresh(usage_record)

        return usage_record

    @staticmethod
    def calculate_cost(
        input_tokens: int,
        output_tokens: int,
        cost_per_1k_tokens: Optional[float]
    ) -> Optional[float]:
        """
        Calculate estimated cost based on token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost_per_1k_tokens: Cost per 1000 tokens (if known)

        Returns:
            Estimated cost in USD, or None if cost_per_1k_tokens not provided
        """
        if cost_per_1k_tokens is None:
            return None

        total_tokens = input_tokens + output_tokens
        return (total_tokens / 1000.0) * cost_per_1k_tokens
