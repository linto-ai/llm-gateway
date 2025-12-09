#!/usr/bin/env python3
"""Pydantic schemas for flavor analytics and usage tracking."""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class TimeSeriesPoint(BaseModel):
    """Single point in time series data."""

    timestamp: datetime
    requests: int
    tokens: int
    cost: float

    class Config:
        from_attributes = True


class FlavorStatsData(BaseModel):
    """Detailed statistics data for a flavor."""

    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float  # Percentage

    # Token usage
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    avg_input_tokens: float
    avg_output_tokens: float

    # Performance
    avg_latency_ms: float
    min_latency_ms: int
    max_latency_ms: int
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float

    # Cost
    total_estimated_cost: float
    avg_cost_per_request: float

    # Time series (hourly for 24h, daily for 7d/30d)
    time_series: List[TimeSeriesPoint]


class FlavorStats(BaseModel):
    """Statistics for a single flavor."""

    flavor_id: UUID
    flavor_name: str
    period: str
    stats: FlavorStatsData
    generated_at: datetime

    class Config:
        from_attributes = True


class FlavorComparison(BaseModel):
    """Comparison data for a single flavor."""

    flavor_id: UUID
    flavor_name: str
    is_default: bool
    total_requests: int
    success_rate: float
    total_tokens: int
    avg_latency_ms: float
    total_estimated_cost: float
    usage_percentage: float  # % of total service requests

    class Config:
        from_attributes = True


class ServiceFlavorComparisonTotals(BaseModel):
    """Totals for all flavors in a service."""

    total_requests: int
    total_tokens: int
    total_cost: float


class ServiceFlavorComparison(BaseModel):
    """Comparison of all flavors for a service."""

    service_id: UUID
    service_name: str
    period: str
    flavors: List[FlavorComparison]
    totals: ServiceFlavorComparisonTotals
    generated_at: datetime

    class Config:
        from_attributes = True


class FlavorUsageRecord(BaseModel):
    """Individual usage record."""

    id: UUID
    flavor_id: UUID
    job_id: Optional[UUID]
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: int
    estimated_cost: Optional[float]
    success: bool
    error_message: Optional[str]
    executed_at: datetime

    class Config:
        from_attributes = True


class FlavorUsageHistory(BaseModel):
    """Paginated flavor usage history."""

    total: int
    items: List[FlavorUsageRecord]

    class Config:
        from_attributes = True
