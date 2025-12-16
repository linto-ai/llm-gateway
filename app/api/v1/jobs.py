"""Jobs API router."""
import json
import logging
import asyncio
import traceback
from datetime import datetime
from typing import Optional, List, Literal as TypeLiteral
from uuid import UUID
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
import redis.asyncio as aioredis

from app.api.dependencies import get_db
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.services.job_service import job_service
from app.services.job_result_version_service import job_result_version_service
from app.models.job import Job
from app.models.model import Model
from app.schemas.job import (
    JobResponse, JobCancelResponse, JobUpdate, JobProgress, RetryInfo,
    JobMetricsResponse, JobFinalSummary, CurrentPassMetrics, CumulativeMetrics,
    JobResultUpdate, JobVersionSummary, JobVersionDetail,
    ActiveJobSnapshot, JobsSnapshotMessage, JobUpdateBroadcast
)
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.http_server.celery_app import get_task_status_async

logger = logging.getLogger(__name__)


def _get_redis_url():
    """Get Redis URL for async client."""
    parsed_url = urlparse(settings.services_broker)
    broker_pass = settings.services_broker_password
    return f"redis://:{broker_pass}@{parsed_url.hostname}:{parsed_url.port or 6379}/2"

# Terminal job states that close WebSocket connection
TERMINAL_STATES = {'completed', 'failed', 'cancelled'}

# Non-terminal states to monitor for global WebSocket
# Note: 'pending' is not a valid status per Job model constraint; actual active states are:
ACTIVE_STATES = {'queued', 'started', 'processing'}

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_job(
    job_id: UUID,
    format: Optional[TypeLiteral["raw", "text", "json", "md"]] = Query(
        None,
        description="Output format transformation: raw (default), text, json, md"
    ),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """
    Get job status and result by job ID.

    Synchronizes status with Celery backend before returning.

    Query Parameters:
    - format: Optional transformation for the result
      - raw: Return result as stored (default)
      - text: Extract output as plain text
      - json: Return result as JSON object
      - md: Return output formatted for markdown display
    """
    job = await job_service.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Apply format transformation if requested and result exists
    if format and format != "raw" and job.result:
        job = _apply_format_transformation(job, format)

    return job


def _apply_format_transformation(
    job: JobResponse,
    format: str
) -> JobResponse:
    """Apply format transformation to job result."""
    result = job.result

    if format == "text":
        # Extract plain text from result
        if isinstance(result, dict) and "output" in result:
            content = result["output"]
        elif isinstance(result, dict):
            content = str(result)
        else:
            content = str(result)
        # Return as text wrapper
        job.result = {"output": content, "format": "text"}

    elif format == "json":
        # Ensure result is JSON-serializable
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                result = {"output": result}
        job.result = result if isinstance(result, dict) else {"output": result}

    elif format == "md":
        # Format for markdown display
        if isinstance(result, dict) and "output" in result:
            content = result["output"]
        elif isinstance(result, str):
            content = result
        else:
            content = str(result)
        job.result = {"output": content, "format": "markdown"}

    return job


@router.get(
    "/{job_id}/metrics",
    response_model=JobMetricsResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_job_metrics(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JobMetricsResponse:
    """
    Get detailed token metrics for a job.

    Returns:
    - job_id: The job UUID
    - status: Current job status
    - token_metrics: Detailed breakdown of token usage per pass
    - final_summary: Aggregated summary (only for completed jobs)
    """
    job = await job_service.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Build final summary for completed jobs
    final_summary = None
    if job.status == "completed" and job.token_metrics:
        final_summary = JobFinalSummary(
            total_tokens=job.token_metrics.total_tokens,
            total_duration_ms=job.token_metrics.total_duration_ms,
            total_passes=len(job.token_metrics.passes),
            total_estimated_cost=job.token_metrics.total_estimated_cost,
        )

    return JobMetricsResponse(
        job_id=str(job_id),
        status=job.status,
        token_metrics=job.token_metrics,
        final_summary=final_summary,
    )


@router.get(
    "",
    response_model=PaginatedResponse[JobResponse],
    responses={500: {"model": ErrorResponse}},
)
async def list_jobs(
    service_id: Optional[UUID] = Query(None, description="Filter by service"),
    status: Optional[str] = Query(None, description="Filter by status"),
    organization_id: Optional[str] = Query(None, max_length=100, description="Filter by organization (free-form string)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[JobResponse]:
    """
    List jobs with optional filtering and pagination.
    """
    try:
        skip = (page - 1) * page_size
        items, total = await job_service.list_jobs(
            db=db,
            service_id=service_id,
            status=status,
            organization_id=organization_id,
            skip=skip,
            limit=page_size,
        )

        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}",
        )


@router.post(
    "/cleanup-stale",
    responses={200: {"description": "Stale jobs cleanup result"}},
)
async def cleanup_stale_jobs(
    timeout_minutes: int = Query(
        30,
        ge=5,
        le=1440,
        description="Minutes after which an active job is considered stale (5-1440)"
    ),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Detect and mark stale jobs as failed (time-based).

    Stale jobs are those stuck in queued/started/processing states for longer
    than the timeout. This typically happens when Celery workers are killed
    or crash during job execution.

    - **timeout_minutes**: How long a job must be stuck before being marked stale (default: 30)

    Returns list of jobs that were marked as failed.

    Note: For smarter detection that checks actual Celery state, use /cleanup-orphaned instead.
    """
    marked_jobs = await job_service.mark_stale_jobs_failed(db, timeout_minutes)

    return {
        "status": "success",
        "marked_count": len(marked_jobs),
        "marked_jobs": marked_jobs,
        "message": f"Marked {len(marked_jobs)} stale jobs as failed" if marked_jobs else "No stale jobs found",
    }


@router.post(
    "/cleanup-expired",
    responses={200: {"description": "Expired jobs cleanup result"}},
)
async def cleanup_expired_jobs(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete jobs that have exceeded their TTL (expires_at in the past).

    Jobs with NULL expires_at are never deleted by this endpoint.
    This cleans up jobs from flavors that have a default_ttl_seconds configured.

    Returns the count of deleted jobs.
    """
    from app.models.job import Job

    # Delete expired jobs
    result = await db.execute(
        select(Job).where(
            Job.expires_at.isnot(None),
            Job.expires_at < datetime.utcnow()
        )
    )
    expired_jobs = result.scalars().all()
    deleted_count = len(expired_jobs)

    for job in expired_jobs:
        await db.delete(job)

    await db.commit()

    logger.info(f"Cleaned up {deleted_count} expired jobs")

    return {
        "status": "success",
        "deleted_count": deleted_count,
        "message": f"Deleted {deleted_count} expired jobs" if deleted_count else "No expired jobs found",
    }


@router.post(
    "/cleanup-orphaned",
    responses={200: {"description": "Orphaned jobs cleanup result"}},
)
async def cleanup_orphaned_jobs(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Detect and cleanup orphaned jobs by checking Celery task state.

    This is smarter than time-based cleanup (/cleanup-stale). It checks each active job's
    Celery task state to determine if a worker is actually processing it:

    - **UNKNOWN**: Task not found in Celery (worker died, task lost)
    - **SUCCESS**: Task completed but DB wasn't updated (recovers result if available)
    - **FAILURE**: Task failed but DB wasn't updated
    - **REVOKED**: Task was cancelled

    Jobs with mismatched states are updated accordingly:
    - SUCCESS in Celery -> completed in DB (with recovered result)
    - FAILURE/REVOKED/UNKNOWN -> failed in DB

    This endpoint is also called periodically by the server (configurable via STALE_JOB_CHECK_INTERVAL).
    """
    cleaned_jobs = await job_service.cleanup_orphaned_jobs(db)

    return {
        "status": "success",
        "cleaned_count": len(cleaned_jobs),
        "cleaned_jobs": cleaned_jobs,
        "message": f"Cleaned {len(cleaned_jobs)} orphaned jobs" if cleaned_jobs else "No orphaned jobs found",
    }


@router.post(
    "/{job_id}/cancel",
    response_model=JobCancelResponse,
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
)
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JobCancelResponse:
    """
    Cancel a queued or processing job.

    Attempts to revoke the Celery task and update the job status.

    - **job_id**: Job UUID to cancel

    Returns cancellation status and message.
    """
    result = await job_service.cancel_job(db, job_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    if result["status"] == "failed" and "Cannot cancel" in result["message"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )

    return JobCancelResponse(**result)


@router.delete(
    "/{job_id}",
    responses={
        200: {"description": "Job deleted successfully"},
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
)
async def delete_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete a job permanently.

    Only completed, failed, or cancelled jobs can be deleted.
    Active jobs (queued, started, processing) must be cancelled first.

    - **job_id**: Job UUID to delete

    Returns confirmation of deletion.
    """
    # Get the job first
    job = await job_service.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Check if job is in terminal state
    if job.status not in TERMINAL_STATES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete job in '{job.status}' state. Cancel it first."
        )

    # Delete the job
    await job_service.delete_job(db, job_id)

    return {
        "status": "success",
        "message": f"Job {job_id} deleted successfully",
        "job_id": str(job_id),
    }


async def _get_job_for_ws(db: AsyncSession, job_id: UUID) -> Optional[Job]:
    """Get job with relationships for WebSocket updates."""
    stmt = (
        select(Job)
        .options(joinedload(Job.service), joinedload(Job.flavor))
        .where(Job.id == job_id)
    )
    result = await db.execute(stmt)
    return result.unique().scalar_one_or_none()


def _build_job_update_from_celery_data(
    job: Job,
    celery_status: Optional[str],
    celery_result,
    celery_progress: Optional[str]
) -> JobUpdate:
    """Build JobUpdate message from Job model and pre-fetched Celery data."""
    celery_meta = {}

    # Process Celery data if available
    if celery_status == 'PROGRESS':
        # celery_result may be a dict with detailed progress info
        if isinstance(celery_result, dict):
            celery_meta = celery_result
        elif celery_progress:
            # celery_progress is a percentage string like "50"
            celery_meta = {'percentage': float(celery_progress)}
    elif celery_status == 'SUCCESS' and celery_result is not None:
        # Pass the Celery result for completed jobs
        celery_meta = {'celery_result': celery_result}

    return _build_job_update_internal(job, celery_status, celery_meta)


async def _build_job_update_async(job: Job, celery_task_id: Optional[str] = None) -> JobUpdate:
    """Build JobUpdate message from Job model and Celery status (async - non-blocking)."""
    celery_status = None
    celery_result = None
    celery_progress = None

    # First try to get progress from Celery (real-time) - using async version
    if celery_task_id:
        try:
            celery_status, celery_result, celery_progress = await get_task_status_async(celery_task_id)
        except Exception as e:
            logger.debug(f"Could not get Celery progress: {e}")

    return _build_job_update_from_celery_data(job, celery_status, celery_result, celery_progress)


def _build_job_update_internal(
    job: Job,
    celery_status: Optional[str],
    celery_meta: dict
) -> JobUpdate:
    """Internal helper to build JobUpdate from processed data."""
    progress = None
    event_type = 'status_change'
    retry_info = None
    current_pass_metrics = None
    cumulative_metrics = None

    # Extract event_type from Celery meta (set by batch_manager on retry)
    event_type = celery_meta.get('event_type', 'progress' if celery_meta else 'status_change')

    # Extract retry_info if present
    if 'retry_info' in celery_meta:
        try:
            retry_info = RetryInfo(**celery_meta['retry_info'])
        except Exception:
            pass

    # Extract current pass metrics from Celery meta
    if 'current_pass_metrics' in celery_meta and celery_meta['current_pass_metrics']:
        try:
            cpm = celery_meta['current_pass_metrics']
            current_pass_metrics = CurrentPassMetrics(
                pass_number=cpm['pass_number'],
                pass_type=cpm['pass_type'],
                prompt_tokens=cpm['prompt_tokens'],
                completion_tokens=cpm['completion_tokens'],
                duration_ms=cpm['duration_ms'],
            )
        except Exception:
            pass

    # Extract cumulative metrics from Celery meta
    if 'cumulative_metrics' in celery_meta and celery_meta['cumulative_metrics']:
        try:
            cm = celery_meta['cumulative_metrics']
            cumulative_metrics = CumulativeMetrics(
                total_tokens=cm['total_tokens'],
                total_prompt_tokens=cm['total_prompt_tokens'],
                total_completion_tokens=cm['total_completion_tokens'],
                total_duration_ms=cm['total_duration_ms'],
                total_estimated_cost=cm.get('total_estimated_cost'),
            )
        except Exception:
            pass

    # Build enhanced progress from Celery meta or job.progress
    meta = celery_meta or job.progress or {}
    if meta:
        try:
            # Calculate percentage from completed_turns/total_turns if not provided
            completed = meta.get('completed_turns', meta.get('current', 0))
            total = meta.get('total_turns', meta.get('total', 1)) or 1
            calculated_pct = round(100.0 * completed / total, 1) if total > 0 else 0.0
            percentage = meta.get('percentage', calculated_pct)

            progress = JobProgress(
                current=completed,
                total=total,
                percentage=percentage,
                phase=meta.get('phase', 'processing'),
                current_batch=meta.get('current_batch', 0),
                total_batches=meta.get('total_batches', 1),
                completed_turns=meta.get('completed_turns', 0),
                total_turns=meta.get('total_turns', 0),
                estimated_seconds_remaining=meta.get('estimated_seconds_remaining'),
                total_retries=meta.get('total_retries', 0),
            )
        except Exception:
            # Fallback to basic progress
            current = meta.get('current', 0)
            total = meta.get('total', 1) or 1
            calculated_pct = round(100.0 * current / total, 1) if total > 0 else 0.0
            progress = JobProgress(
                current=current,
                total=total,
                percentage=meta.get('percentage', calculated_pct)
            )

    # Determine effective status (prefer Celery for real-time, fallback to DB)
    effective_status = job.status
    if celery_status:
        status_map = {
            'QUEUED': 'queued',
            'STARTED': 'started',
            'PROGRESS': 'processing',
            'SUCCESS': 'completed',
            'FAILURE': 'failed',
        }
        if celery_status in status_map:
            effective_status = status_map[celery_status]

    # Set event_type based on status
    if effective_status in ('completed', 'failed', 'cancelled'):
        event_type = 'complete'

    # Determine result - prefer Celery result (real-time) over DB result
    result = None
    if effective_status == 'completed':
        # First try Celery result (more up-to-date), then fall back to DB
        result = celery_meta.get('celery_result') or job.result

    return JobUpdate(
        job_id=str(job.id),
        event_type=event_type,
        status=effective_status,
        progress=progress,
        result=result,
        error=job.error if effective_status in ('failed', 'cancelled') else None,
        retry_info=retry_info,
        timestamp=datetime.utcnow().isoformat(),
        current_pass_metrics=current_pass_metrics,
        cumulative_metrics=cumulative_metrics,
    )


# WebSocket endpoint for real-time job monitoring
# Note: This is registered on the main app via a separate include to avoid prefix issues
async def websocket_job_status(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job status monitoring.

    Pushes JobUpdate messages when job state changes.
    Closes connection on terminal state (completed, failed, cancelled).

    Connection URL: ws://host:port/ws/jobs/{job_id}
    """
    await websocket.accept()

    try:
        # Validate job_id format
        try:
            job_uuid = UUID(job_id)
        except ValueError:
            await websocket.send_json({
                "error": "Invalid job ID format",
                "job_id": job_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            await websocket.close(code=1008)  # Policy violation
            return

        # Track last sent state to avoid duplicate updates
        last_status = None
        last_progress_pct = None
        celery_task_id = None

        while True:
            async with AsyncSessionLocal() as db:
                job = await _get_job_for_ws(db, job_uuid)

                if not job:
                    await websocket.send_json({
                        "error": "Job not found",
                        "job_id": job_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    await websocket.close(code=1008)
                    return

                # Get celery_task_id once
                if not celery_task_id:
                    celery_task_id = job.celery_task_id

                # Build update with Celery progress (using async version to avoid blocking)
                update = await _build_job_update_async(job, celery_task_id)
                current_status = update.status
                current_progress_pct = update.progress.percentage if update.progress else None

                # Send if state or progress changed
                if current_status != last_status or current_progress_pct != last_progress_pct:
                    await websocket.send_json(update.model_dump())

                    last_status = current_status
                    last_progress_pct = current_progress_pct

                # Close on terminal state
                if current_status in TERMINAL_STATES:
                    await websocket.close(code=1000)  # Normal closure
                    return

            # Adaptive polling: faster during processing
            poll_interval = 0.5 if last_status == 'processing' else 2.0
            await asyncio.sleep(poll_interval)

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from WebSocket for job_id: {job_id}")
    except asyncio.CancelledError:
        logger.info(f"WebSocket for job {job_id} cancelled (server shutdown)")
        raise
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
        try:
            await websocket.close(code=1011)  # Internal error
        except Exception:
            pass  # Connection may already be closed


# Global Jobs WebSocket - monitors ALL active jobs via Redis pub/sub
async def websocket_jobs_status(websocket: WebSocket, organization_id: Optional[str] = None):
    """
    WebSocket endpoint for monitoring ALL active jobs.

    Sends:
    1. Initial jobs_snapshot with all active jobs
    2. job_update messages when any job changes (via Redis pub/sub)

    Query parameters:
    - organization_id: Filter jobs by organization (optional, free-form string)

    Connection URL: ws://host:port/ws/jobs or ws://host:port/ws/jobs?organization_id=my-org
    """
    await websocket.accept()
    org_filter_msg = f" (organization_id={organization_id})" if organization_id else ""
    logger.info(f"Global jobs WebSocket accepted{org_filter_msg}, using Redis pub/sub")

    redis_client = None
    pubsub = None

    try:
        # Send initial snapshot
        async with AsyncSessionLocal() as db:
            stmt = (
                select(Job)
                .options(joinedload(Job.service), joinedload(Job.flavor))
                .where(Job.status.in_(ACTIVE_STATES))
            )
            if organization_id:
                stmt = stmt.where(Job.organization_id == organization_id)
            stmt = stmt.order_by(Job.created_at.desc())
            result = await db.execute(stmt)
            jobs = result.unique().scalars().all()

            snapshots = []
            for job in jobs:
                celery_task_id = job.celery_task_id
                update = await _build_job_update_async(job, celery_task_id)
                snapshots.append(ActiveJobSnapshot(
                    job_id=str(job.id),
                    status=update.status,
                    progress=update.progress,
                    service_name=job.service.name if job.service else None,
                    flavor_name=job.flavor.name if job.flavor else None,
                    created_at=job.created_at,
                ))

            logger.debug(f"Global WS: sending initial snapshot with {len(snapshots)} active jobs")
            await websocket.send_json(JobsSnapshotMessage(
                jobs=snapshots,
                timestamp=datetime.utcnow(),
            ).model_dump(mode='json'))

        # Subscribe to Redis pub/sub for job updates
        redis_client = aioredis.from_url(_get_redis_url())
        pubsub = redis_client.pubsub()

        # Subscribe to organization-specific channel or global channel
        if organization_id:
            channel = f"job_updates:{organization_id}"
        else:
            channel = "job_updates:global"

        await pubsub.subscribe(channel)
        logger.info(f"Global WS: subscribed to Redis channel '{channel}'")

        # Listen for messages from Redis pub/sub with timeout for clean shutdown
        while True:
            try:
                # Use get_message with timeout instead of blocking listen()
                # This allows the loop to be interrupted during shutdown
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=5.0
                )

                if message is None:
                    # No message received, check if websocket is still open
                    continue

                if message["type"] == "message":
                    data = json.loads(message["data"])
                    job_id = data.get("job_id")
                    msg_org_id = data.get("organization_id")

                    # Filter by organization if specified
                    if organization_id and msg_org_id != organization_id:
                        continue

                    logger.debug(f"Global WS: received Redis update for job {job_id}, status={data.get('status')}")

                    # Build progress object only if it has required fields
                    progress_data = data.get("progress")
                    progress_obj = None
                    if progress_data and isinstance(progress_data, dict):
                        if all(k in progress_data for k in ('current', 'total', 'percentage')):
                            progress_obj = progress_data

                    # Send update to WebSocket client
                    await websocket.send_json(JobUpdateBroadcast(
                        job_id=job_id,
                        status=data.get("status"),
                        progress=progress_obj,
                        result=data.get("result"),
                        error=data.get("error"),
                        timestamp=datetime.utcnow(),
                    ).model_dump(mode='json'))

            except asyncio.TimeoutError:
                # Timeout is normal, just continue the loop
                continue
            except json.JSONDecodeError as e:
                logger.warning(f"Global WS: failed to parse Redis message: {e}")
            except WebSocketDisconnect:
                logger.info("Client disconnected during message processing")
                return
            except RuntimeError as e:
                # WebSocket already closed
                if "close" in str(e).lower():
                    logger.info("WebSocket closed, stopping Redis listener")
                    return
                raise
            except Exception as e:
                logger.error(f"Global WS: error processing message: {e}")

    except WebSocketDisconnect:
        logger.info("Client disconnected from global jobs WebSocket")
    except asyncio.CancelledError:
        logger.info("Global jobs WebSocket cancelled (server shutdown)")
        raise  # Re-raise to allow proper cleanup
    except Exception as e:
        logger.error(f"Global jobs WebSocket error: {e}\n{traceback.format_exc()}")
        try:
            await websocket.send_json({
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        # Clean up Redis connection
        if pubsub:
            try:
                await pubsub.unsubscribe()
                await pubsub.close()
            except Exception:
                pass
        if redis_client:
            try:
                await redis_client.close()
            except Exception:
                pass


@router.patch(
    "/{job_id}/result",
    response_model=JobResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def update_job_result(
    job_id: UUID,
    update_data: JobResultUpdate,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """
    Update job result content. Creates a new version with diff storage.

    - **job_id**: Job UUID
    - **content**: New result content (required)

    Only completed jobs can be edited.
    """
    # Get job to validate state
    job = await job_service.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only edit completed jobs"
        )

    # Create new version
    version = await job_result_version_service.create_version(
        db, job_id, update_data.content, created_by=None
    )

    if not version:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create version"
        )

    await db.commit()

    # Return updated job
    updated_job = await job_service.get_job_by_id(db, job_id)
    return updated_job


@router.get(
    "/{job_id}/versions",
    response_model=List[JobVersionSummary],
    responses={404: {"model": ErrorResponse}},
)
async def list_job_versions(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> List[JobVersionSummary]:
    """
    List version history for a job.

    Returns summaries of all versions including version number,
    creation timestamp, and content length.
    """
    versions = await job_result_version_service.list_versions(db, job_id)
    if versions is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    return versions


@router.get(
    "/{job_id}/versions/{version_number}",
    response_model=JobVersionDetail,
    responses={404: {"model": ErrorResponse}},
)
async def get_job_version(
    job_id: UUID,
    version_number: int,
    db: AsyncSession = Depends(get_db),
) -> JobVersionDetail:
    """
    Get specific version content (fully reconstructed).

    - **job_id**: Job UUID
    - **version_number**: Version to retrieve (1 = original, 2+ = edits)
    """
    # First check if job exists
    job = await job_service.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    version = await job_result_version_service.get_version(db, job_id, version_number)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )
    return version


@router.post(
    "/{job_id}/versions/{version_number}/restore",
    response_model=JobResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def restore_job_version(
    job_id: UUID,
    version_number: int,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """
    Restore job to a previous version. Creates a new version entry.

    - **job_id**: Job UUID
    - **version_number**: Version to restore

    Cannot restore to current version.
    """
    # Get job to validate state and check version
    job = await job_service.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    if version_number == job.current_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot restore to current version"
        )

    # Check that version exists before attempting restore
    version = await job_result_version_service.get_version(db, job_id, version_number)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    # Restore the version
    restored_job = await job_result_version_service.restore_version(
        db, job_id, version_number, created_by=None
    )

    if not restored_job:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore version"
        )

    await db.commit()

    # Return updated job
    return await job_service.get_job_by_id(db, job_id)


@router.get(
    "/{job_id}/export/{format}",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {},
                "application/pdf": {},
                "text/html": {},
            }
        },
    },
)
async def export_job_result(
    job_id: UUID,
    format: TypeLiteral["docx", "pdf", "html"],
    template_id: Optional[UUID] = Query(None, description="Template to use (falls back to default)"),
    version_number: Optional[int] = Query(None, description="Specific version to export (uses version content and per-version extraction cache)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Export job result as DOCX, PDF, or HTML with just-in-time extraction.

    Behavior:
    1. Load template (specified or default)
    2. Parse template placeholders
    3. If version_number specified, fetch that version's content and use per-version extraction cache
    4. Check which placeholders are already in extracted_metadata (main or per-version)
    4. If missing placeholders exist AND flavor has extraction prompt configured:
       - Perform just-in-time extraction for missing fields only
       - Update job.result.extracted_metadata with new values
       - Record extraction in job token metrics
    5. Generate document with all available placeholder values
    """
    from fastapi.responses import StreamingResponse
    from app.services.document_template_service import document_template_service
    from app.services.document_service import document_service
    from app.services.export_service import export_service
    from app.services.provider_service import provider_service
    from app.models.service_flavor import ServiceFlavor

    job = await job_service.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only export completed jobs"
        )

    # Get job with relationships for document generation
    stmt = (
        select(Job)
        .options(joinedload(Job.service), joinedload(Job.flavor))
        .where(Job.id == job_id)
    )
    result = await db.execute(stmt)
    job = result.unique().scalar_one_or_none()

    # Get template (optional - DocumentService will use default if not provided)
    template = None
    if template_id:
        template = await document_template_service.get_template(db, template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        # Verify template file exists
        template_path = document_service.TEMPLATES_DIR / template.file_path
        if not template_path.exists():
            logger.warning(f"Template file not found: {template_path}, using built-in default")
            template = None
    else:
        # First check if the job's service has a default template
        if job.service and job.service.default_template_id:
            template = await document_template_service.get_template(db, job.service.default_template_id)
            if template:
                template_path = document_service.TEMPLATES_DIR / template.file_path
                if not template_path.exists():
                    logger.warning(f"Service default template file not found: {template_path}, using built-in default")
                    template = None
        # Fall back to global default template
        if not template:
            template = await document_template_service.get_default_template(db)
            # Verify template file exists if we got one
            if template:
                template_path = document_service.TEMPLATES_DIR / template.file_path
                if not template_path.exists():
                    logger.warning(f"Default template file not found: {template_path}, using built-in default")
                    template = None

    # Prepare LLM inference for JIT extraction (if flavor has extraction prompt)
    llm_inference = None
    if job.flavor_id:
        try:
            # Get flavor with model and provider
            from sqlalchemy.orm import joinedload as jl
            flavor_stmt = (
                select(ServiceFlavor)
                .options(
                    jl(ServiceFlavor.model).joinedload(Model.provider)
                )
                .where(ServiceFlavor.id == job.flavor_id)
            )
            flavor_result = await db.execute(flavor_stmt)
            flavor = flavor_result.unique().scalar_one_or_none()

            if flavor and flavor.placeholder_extraction_prompt_id and flavor.model:
                # Get decrypted API key
                decrypted_key = await provider_service.get_decrypted_api_key(db, flavor.model.provider_id)

                # Create LLM wrapper for extraction
                class ExtractionLLM:
                    def __init__(self, model, api_key, api_url):
                        from openai import AsyncOpenAI
                        self.client = AsyncOpenAI(api_key=api_key, base_url=api_url)
                        self.model_name = model.model_identifier

                    async def generate(self, messages, temperature=0.1, max_tokens=2000):
                        response = await self.client.chat.completions.create(
                            model=self.model_name,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                        return response.choices[0].message.content

                llm_inference = ExtractionLLM(
                    flavor.model,
                    decrypted_key,
                    flavor.model.provider.api_base_url
                )
        except Exception as e:
            logger.warning(f"Could not prepare LLM for JIT extraction: {e}")

    # Generate document with JIT extraction
    try:
        content = await export_service.export_with_extraction(
            db=db,
            job=job,
            template=template,
            format=format,
            llm_inference=llm_inference,
            version_number=version_number,
        )
        await db.commit()  # Commit any JIT extraction updates
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document generation unavailable: {str(e)}"
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

    if format == "docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext = "docx"
    elif format == "html":
        # HTML is returned as string, not BytesIO
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=content, status_code=200)
    else:
        media_type = "application/pdf"
        ext = "pdf"

    service_name = job.service.name if job.service else "job"
    filename = f"{service_name}_{job.id}.{ext}"

    return StreamingResponse(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post(
    "/{job_id}/export-preview",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def export_preview(
    job_id: UUID,
    template_id: Optional[UUID] = Query(None, description="Template to preview (uses default if not specified)"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Preview export placeholders and extraction status.

    Returns information about which placeholders will be filled:
    - available: Value is already in extracted_metadata
    - extraction_required: Value can be extracted via JIT extraction
    - missing: Value is not available and cannot be extracted
    """
    from app.services.document_template_service import document_template_service
    from app.services.export_service import export_service

    job = await job_service.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only preview export for completed jobs"
        )

    # Get job with relationships
    stmt = (
        select(Job)
        .options(joinedload(Job.service), joinedload(Job.flavor))
        .where(Job.id == job_id)
    )
    result = await db.execute(stmt)
    job = result.unique().scalar_one_or_none()

    # Get template
    template = None
    if template_id:
        template = await document_template_service.get_template(db, template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
    else:
        # First check if the job's service has a default template
        if job.service and job.service.default_template_id:
            template = await document_template_service.get_template(db, job.service.default_template_id)
        # Fall back to global default template
        if not template:
            template = await document_template_service.get_default_template(db)

    # Get preview
    preview = await export_service.get_export_preview(db, job, template)

    return preview


router_name = "jobs"
