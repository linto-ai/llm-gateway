#!/usr/bin/env python3
"""Analytics API endpoints for dashboard and system-wide statistics.

Provides dashboard health overview endpoint.
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import DashboardAnalytics

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analytics"])


@router.get(
    "/analytics/dashboard",
    response_model=DashboardAnalytics,
)
async def get_dashboard_analytics(
    db: AsyncSession = Depends(get_db),
) -> DashboardAnalytics:
    """
    Get system-wide health overview for the last 24 hours.

    Returns:
    - **overview**: Aggregate metrics (jobs, tokens, cost, latency)
    - **services**: Per-service health status
    - **recent_failures**: 5 most recent failed jobs

    Health status logic:
    - healthy: success_rate >= 95%
    - degraded: success_rate >= 80% and < 95%
    - unhealthy: success_rate < 80%
    - inactive: no requests in 24h period
    """
    return await AnalyticsService.get_dashboard_analytics(db)
