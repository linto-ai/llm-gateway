#!/usr/bin/env python3
"""
LLM Gateway - FastAPI HTTP Server

This is the main entry point for the LLM Gateway API.
All endpoints are documented at /docs (Swagger UI).

API Version: v1
Base Path: /api/v1
"""
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import urlparse
import redis

from app.http_server.celery_app import clean_old_task_ids
from app.api.v1 import (
    providers, health, models, services as services_api,
    prompts, service_templates, jobs, service_flavors,
    synthetic_templates, huggingface, flavor_presets, service_types, prompt_types,
    tokenizers, analytics, templates
)
from app.api.v1.jobs import websocket_job_status, websocket_jobs_status
from app.core.config import settings as pydantic_settings
from app.services.model_service import model_service
from app.services.provider_service import provider_service
from app.services.job_service import job_service

# Logging Setup
logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)
logger = logging.getLogger("http_server")
logger.setLevel(logging.DEBUG if pydantic_settings.debug else logging.INFO)


# Filter out healthcheck logs from uvicorn
class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.args and len(record.args) >= 3 and record.args[2] != "/healthcheck"


logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

# Initialize Redis client for task cleanup
services_broker = pydantic_settings.services_broker
broker_pass = pydantic_settings.services_broker_password if pydantic_settings.services_broker_password != "EMPTY" else None
parsed_url = urlparse(services_broker)
redis_client = redis.Redis(host=parsed_url.hostname, port=parsed_url.port, password=broker_pass)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    from app.core.database import AsyncSessionLocal

    # Startup: Detect and cleanup orphaned jobs (smarter Celery-based detection)
    async with AsyncSessionLocal() as db:
        try:
            cleaned_jobs = await job_service.cleanup_orphaned_jobs(db)
            if cleaned_jobs:
                logger.warning(f"Startup: Cleaned {len(cleaned_jobs)} orphaned jobs")
                for job_info in cleaned_jobs:
                    logger.info(
                        f"  - Job {job_info['job_id']}: {job_info['previous_status']} -> {job_info['new_status']} "
                        f"(celery={job_info['celery_status']}, action={job_info['action']})"
                    )
        except Exception as e:
            logger.error(f"Startup orphaned job cleanup failed: {e}")

    # Startup: Model verification for all providers (non-blocking)
    async with AsyncSessionLocal() as db:
        try:
            providers_list, total = await provider_service.list_providers(db, page=1, limit=1000)

            for provider in providers_list:
                try:
                    logger.info(f"Verifying models for provider: {provider.name}")
                    verification = await model_service.verify_provider_models(db, provider.id)
                    logger.info(f"Verified {verification.verified_count}/{verification.total_models} models for {provider.name}")

                    if verification.failed_count > 0:
                        logger.warning(f"Failed to verify {verification.failed_count} models for {provider.name}")
                except Exception as e:
                    logger.error(f"Error verifying models for provider {provider.name}: {e}")
        except Exception as e:
            logger.error(f"Startup verification failed: {e}")

    # Start periodic cleanup tasks
    cleanup_task = asyncio.create_task(periodic_cleanup())
    orphan_monitor_task = asyncio.create_task(periodic_orphan_monitor())

    yield

    # Shutdown: Cancel cleanup tasks
    cleanup_task.cancel()
    orphan_monitor_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    try:
        await orphan_monitor_task
    except asyncio.CancelledError:
        pass


# FastAPI App Setup
app = FastAPI(
    title=pydantic_settings.app_name,
    description=pydantic_settings.app_description,
    version="1.0.0",
    docs_url=pydantic_settings.docs_url,
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=pydantic_settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 API routers
app.include_router(providers.router, prefix=pydantic_settings.api_v1_prefix)
app.include_router(models.router, prefix=pydantic_settings.api_v1_prefix)
app.include_router(services_api.router, prefix=pydantic_settings.api_v1_prefix)
app.include_router(prompts.router, prefix=pydantic_settings.api_v1_prefix)
app.include_router(service_templates.router, prefix=pydantic_settings.api_v1_prefix)
app.include_router(jobs.router, prefix=pydantic_settings.api_v1_prefix)
app.include_router(service_flavors.router, prefix=pydantic_settings.api_v1_prefix)
app.include_router(synthetic_templates.router, prefix=pydantic_settings.api_v1_prefix)
app.include_router(huggingface.router, prefix=pydantic_settings.api_v1_prefix)
app.include_router(flavor_presets.router, prefix=pydantic_settings.api_v1_prefix)
app.include_router(service_types.router, prefix=pydantic_settings.api_v1_prefix)
app.include_router(prompt_types.router, prefix=pydantic_settings.api_v1_prefix)
app.include_router(tokenizers.router, prefix=pydantic_settings.api_v1_prefix)
app.include_router(analytics.router, prefix=pydantic_settings.api_v1_prefix)
app.include_router(templates.router, prefix=pydantic_settings.api_v1_prefix)
app.include_router(health.router)


# WebSocket endpoint for monitoring ALL active jobs
# IMPORTANT: This MUST be registered BEFORE /ws/jobs/{job_id} to avoid route matching issues
@app.websocket("/ws/jobs")
async def ws_jobs_status(websocket: WebSocket, organization_id: Optional[str] = None):
    """
    WebSocket endpoint for monitoring all active jobs.

    Query parameters:
    - organization_id: Filter jobs by organization (optional, free-form string)

    Connect to receive live updates on all jobs in progress.
    See API documentation for message format.
    """
    await websocket_jobs_status(websocket, organization_id=organization_id)


# WebSocket endpoint for real-time job monitoring (single job)
@app.websocket("/ws/jobs/{job_id}")
async def ws_job_status(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job status monitoring.

    Connect to receive live updates on job progress.
    See API documentation for message format.
    """
    await websocket_job_status(websocket, job_id)


async def periodic_cleanup():
    """Periodically clean up old task IDs from Redis."""
    loop = asyncio.get_event_loop()
    while True:
        await asyncio.sleep(pydantic_settings.task_cleanup_interval)
        # Run blocking Redis operations in thread pool
        acquired = await loop.run_in_executor(
            None,
            lambda: redis_client.set("task_cleanup_lock", "1", nx=True, ex=30)
        )
        if acquired:
            await loop.run_in_executor(None, clean_old_task_ids)


async def periodic_orphan_monitor():
    """Periodically check for and cleanup orphaned jobs.

    This monitors active jobs and detects when Celery has lost track of them
    (worker died, task lost, etc).
    """
    from app.core.database import AsyncSessionLocal

    # Wait a bit before first check (let startup complete)
    await asyncio.sleep(60)

    while True:
        try:
            async with AsyncSessionLocal() as db:
                # First check if there are any active jobs to monitor
                active_count = await job_service.get_active_job_count(db)

                if active_count > 0:
                    logger.debug(f"Orphan monitor: checking {active_count} active jobs")
                    cleaned_jobs = await job_service.cleanup_orphaned_jobs(db)

                    if cleaned_jobs:
                        logger.warning(f"Orphan monitor: cleaned {len(cleaned_jobs)} orphaned jobs")
                        for job_info in cleaned_jobs:
                            logger.info(
                                f"  - Job {job_info['job_id']}: {job_info['action']} "
                                f"(celery={job_info['celery_status']})"
                            )
        except Exception as e:
            logger.error(f"Orphan monitor error: {e}")

        # Wait before next check (configurable via env)
        await asyncio.sleep(pydantic_settings.stale_job_check_interval)


def start():
    """Start the FastAPI application."""
    logger.info("Starting FastAPI application...")
    uvicorn.run(
        "app.http_server.ingress:app",
        host="0.0.0.0",
        port=pydantic_settings.service_port,
        workers=pydantic_settings.workers
    )


if __name__ == "__main__":
    start()
