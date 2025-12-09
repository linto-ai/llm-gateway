#!/usr/bin/env python3
import logging
from datetime import datetime
from fastapi import APIRouter
from app.schemas.health import HealthCheckResponse, ConnectionStatus, HealthStatus
from app.core.database import check_db_connection
from app.core.config import settings
import redis

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


async def check_redis_connection() -> bool:
    """Check if Redis connection is healthy."""
    import asyncio

    def _sync_ping():
        from urllib.parse import urlparse
        parsed_url = urlparse(settings.services_broker)
        redis_client = redis.Redis(
            host=parsed_url.hostname,
            port=parsed_url.port or 6379,
            password=settings.services_broker_password if settings.services_broker_password != "EMPTY" else None,
            socket_connect_timeout=2
        )
        redis_client.ping()
        redis_client.close()
        return True

    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_ping)
    except Exception as e:
        logger.error(f"Redis connection check failed: {e}")
        return False


@router.get("/healthcheck", response_model=HealthCheckResponse)
async def healthcheck() -> HealthCheckResponse:
    """
    Health check endpoint.

    Returns system health status including database and Redis connectivity.
    """
    db_connected = await check_db_connection()
    redis_connected = await check_redis_connection()

    overall_status = (
        HealthStatus.HEALTHY
        if db_connected and redis_connected
        else HealthStatus.UNHEALTHY
    )

    return HealthCheckResponse(
        status=overall_status,
        database=ConnectionStatus.CONNECTED if db_connected else ConnectionStatus.DISCONNECTED,
        redis=ConnectionStatus.CONNECTED if redis_connected else ConnectionStatus.DISCONNECTED,
        timestamp=datetime.utcnow()
    )
