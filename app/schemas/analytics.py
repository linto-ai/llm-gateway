#!/usr/bin/env python3
"""Pydantic schemas for analytics dashboard and service statistics."""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
from uuid import UUID


class DashboardOverview(BaseModel):
    """Overview metrics for the analytics dashboard."""

    total_jobs: int = Field(ge=0)
    successful_jobs: int = Field(ge=0)
    failed_jobs: int = Field(ge=0)
    success_rate: float = Field(ge=0, le=100)  # Percentage 0-100
    total_tokens: int = Field(ge=0)
    total_cost: float = Field(ge=0)
    active_services: int = Field(ge=0)
    avg_latency_ms: float = Field(ge=0)


class ServiceHealthSummary(BaseModel):
    """Per-service health summary for the dashboard."""

    service_id: UUID
    service_name: str
    requests_24h: int = Field(ge=0)
    success_rate: float = Field(ge=0, le=100)  # Percentage 0-100
    status: Literal["healthy", "degraded", "unhealthy", "inactive"]

    class Config:
        from_attributes = True


class RecentFailure(BaseModel):
    """Recent job failure information."""

    job_id: UUID
    service_name: str
    error: str
    timestamp: datetime

    class Config:
        from_attributes = True


class DashboardAnalytics(BaseModel):
    """Full dashboard analytics response."""

    period: Literal["24h"] = "24h"
    overview: DashboardOverview
    services: List[ServiceHealthSummary]
    recent_failures: List[RecentFailure]
    generated_at: datetime

    class Config:
        from_attributes = True


class ServiceStatsData(BaseModel):
    """Aggregated statistics for a service."""

    total_requests: int = Field(ge=0)
    successful_requests: int = Field(ge=0)
    failed_requests: int = Field(ge=0)
    success_rate: float = Field(ge=0, le=100)  # Percentage 0-100
    total_tokens: int = Field(ge=0)
    total_estimated_cost: float = Field(ge=0)
    avg_latency_ms: float = Field(ge=0)
    flavors_used: int = Field(ge=0)
    most_used_flavor: Optional[str] = None


class FlavorBreakdownItem(BaseModel):
    """Flavor usage breakdown within a service."""

    flavor_id: UUID
    flavor_name: str
    requests: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)  # Percentage of total requests

    class Config:
        from_attributes = True


class TimeSeriesPoint(BaseModel):
    """Single point in time series data."""

    timestamp: datetime
    requests: int = Field(ge=0)
    tokens: int = Field(ge=0)
    cost: float = Field(ge=0)

    class Config:
        from_attributes = True


class ServiceStats(BaseModel):
    """Full service statistics response."""

    service_id: UUID
    service_name: str
    period: str
    stats: ServiceStatsData
    flavor_breakdown: List[FlavorBreakdownItem]
    time_series: List[TimeSeriesPoint]
    generated_at: datetime

    class Config:
        from_attributes = True
