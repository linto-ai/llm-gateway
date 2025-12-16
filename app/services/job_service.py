"""Job service for managing job execution tracking."""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.job import Job
from app.schemas.job import JobResponse, JobTokenMetrics, JobPassMetrics
from app.http_server.celery_app import get_task_status_async

logger = logging.getLogger(__name__)

# Default timeout for stale job detection (jobs stuck in active states)
DEFAULT_STALE_TIMEOUT_MINUTES = 30


def _extract_token_metrics(progress: Optional[Dict[str, Any]]) -> Optional[JobTokenMetrics]:
    """Extract and validate token metrics from job progress data."""
    if not progress:
        return None

    token_metrics_data = progress.get("token_metrics")
    if not token_metrics_data:
        return None

    try:
        # Parse pass metrics
        passes = []
        for pass_data in token_metrics_data.get("passes", []):
            passes.append(JobPassMetrics(
                pass_number=pass_data["pass_number"],
                pass_type=pass_data["pass_type"],
                started_at=pass_data["started_at"],
                completed_at=pass_data.get("completed_at"),
                duration_ms=pass_data["duration_ms"],
                prompt_tokens=pass_data["prompt_tokens"],
                completion_tokens=pass_data["completion_tokens"],
                total_tokens=pass_data["total_tokens"],
                input_chars=pass_data["input_chars"],
                output_chars=pass_data["output_chars"],
                estimated_cost=pass_data.get("estimated_cost"),
            ))

        return JobTokenMetrics(
            passes=passes,
            total_prompt_tokens=token_metrics_data.get("total_prompt_tokens", 0),
            total_completion_tokens=token_metrics_data.get("total_completion_tokens", 0),
            total_tokens=token_metrics_data.get("total_tokens", 0),
            total_duration_ms=token_metrics_data.get("total_duration_ms", 0),
            total_estimated_cost=token_metrics_data.get("total_estimated_cost"),
            avg_tokens_per_pass=token_metrics_data.get("avg_tokens_per_pass", 0.0),
            avg_duration_per_pass_ms=token_metrics_data.get("avg_duration_per_pass_ms", 0.0),
        )
    except Exception as e:
        logger.debug(f"Failed to parse token metrics: {e}")
        return None


async def _get_celery_progress_async(celery_task_id: str) -> Tuple[Optional[str], Optional[dict]]:
    """Get real-time status and progress from Celery for a task (async - non-blocking)."""
    try:
        celery_status, celery_result, celery_progress_str = await get_task_status_async(celery_task_id)

        # Map Celery status to our status
        status_map = {
            'QUEUED': 'queued',
            'STARTED': 'started',
            'PROGRESS': 'processing',
            'SUCCESS': 'completed',
            'FAILURE': 'failed',
        }
        status = status_map.get(celery_status)

        # Build progress dict if available
        progress = None
        if celery_status == 'PROGRESS' and celery_progress_str:
            percentage = float(celery_progress_str)
            progress = {
                'current': int(percentage),
                'total': 100,
                'percentage': percentage,
            }

        return status, progress
    except Exception as e:
        logger.debug(f"Could not get Celery status for task {celery_task_id}: {e}")
        return None, None


class JobService:
    """Service for job CRUD operations."""

    async def create_job(
        self,
        db: AsyncSession,
        service_id: UUID,
        flavor_id: UUID,
        celery_task_id: str,
        organization_id: Optional[str] = None,
        input_file_name: Optional[str] = None,
        input_preview: Optional[str] = None,
        # Fallback tracking
        fallback_applied: bool = False,
        original_flavor_id: Optional[UUID] = None,
        original_flavor_name: Optional[str] = None,
        fallback_reason: Optional[str] = None,
        fallback_input_tokens: Optional[int] = None,
        fallback_context_available: Optional[int] = None,
        # TTL configuration (from flavor)
        default_ttl_seconds: Optional[int] = None,
    ) -> Job:
        """Create a new job record in the database."""
        # Compute expires_at from TTL if provided
        expires_at = None
        if default_ttl_seconds is not None and default_ttl_seconds > 0:
            expires_at = datetime.utcnow() + timedelta(seconds=default_ttl_seconds)

        job = Job(
            service_id=service_id,
            flavor_id=flavor_id,
            organization_id=organization_id,
            celery_task_id=celery_task_id,
            status="queued",
            input_file_name=input_file_name,
            input_content_preview=input_preview[:500] if input_preview else None,
            # Fallback tracking
            fallback_applied="true" if fallback_applied else "false",
            original_flavor_id=original_flavor_id,
            original_flavor_name=original_flavor_name,
            fallback_reason=fallback_reason,
            fallback_input_tokens=fallback_input_tokens,
            fallback_context_available=fallback_context_available,
            # TTL expiration
            expires_at=expires_at,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    async def get_job_by_id(self, db: AsyncSession, job_id: UUID) -> Optional[JobResponse]:
        """Get job by database ID."""
        stmt = (
            select(Job)
            .options(joinedload(Job.service), joinedload(Job.flavor))
            .where(Job.id == job_id)
        )
        result = await db.execute(stmt)
        job = result.unique().scalar_one_or_none()

        if not job:
            return None

        # Extract token metrics from progress data
        token_metrics = _extract_token_metrics(job.progress)

        # Build proper progress object if we have progress data that isn't just token_metrics
        progress_obj = None
        if job.progress and isinstance(job.progress, dict):
            # Only build JobProgress if we have the required fields
            if all(k in job.progress for k in ('current', 'total', 'percentage')):
                progress_obj = job.progress

        # Get output_type from flavor
        output_type = job.flavor.output_type if job.flavor else "text"

        # Check if flavor has extraction prompt configured
        has_extraction_prompt = bool(
            job.flavor and job.flavor.placeholder_extraction_prompt_id
        )

        # Get processing mode from flavor
        processing_mode = job.flavor.processing_mode if job.flavor else "iterative"

        return JobResponse(
            id=job.id,
            service_id=job.service_id,
            service_name=job.service.name,
            flavor_id=job.flavor_id,
            flavor_name=job.flavor.name if job.flavor else "deleted",
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            result=job.result,
            error=job.error,
            progress=progress_obj,
            organization_id=job.organization_id,
            # Fallback tracking
            fallback_applied=job.fallback_applied == "true",
            original_flavor_id=job.original_flavor_id,
            original_flavor_name=job.original_flavor_name,
            fallback_reason=job.fallback_reason,
            input_tokens=job.fallback_input_tokens,
            context_available=job.fallback_context_available,
            # Token metrics
            token_metrics=token_metrics,
            output_type=output_type,
            current_version=job.current_version,
            last_edited_at=job.last_edited_at,
            has_extraction_prompt=has_extraction_prompt,
            processing_mode=processing_mode,
            # TTL expiration
            expires_at=job.expires_at,
        )

    async def get_job_by_celery_id(self, db: AsyncSession, celery_task_id: str) -> Optional[Job]:
        """Get job by Celery task ID."""
        stmt = select(Job).where(Job.celery_task_id == celery_task_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_job_status(
        self,
        db: AsyncSession,
        celery_task_id: str,
        status: str,
        result: Optional[dict] = None,
        error: Optional[str] = None,
        progress: Optional[dict] = None,
    ) -> Optional[Job]:
        """Update job status (called by Celery worker or polling)."""
        from datetime import datetime

        job = await self.get_job_by_celery_id(db, celery_task_id)
        if not job:
            return None

        job.status = status
        if status == "started" and not job.started_at:
            job.started_at = datetime.utcnow()
        if status in ("completed", "failed") and not job.completed_at:
            job.completed_at = datetime.utcnow()

        if result:
            job.result = result
        if error:
            job.error = error
        if progress:
            job.progress = progress

        await db.commit()
        await db.refresh(job)
        return job

    async def list_jobs(
        self,
        db: AsyncSession,
        service_id: Optional[UUID] = None,
        status: Optional[str] = None,
        organization_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[JobResponse], int]:
        """List jobs with filtering."""
        stmt = select(Job).options(joinedload(Job.service), joinedload(Job.flavor))

        # Apply filters
        if service_id:
            stmt = stmt.where(Job.service_id == service_id)
        if status:
            stmt = stmt.where(Job.status == status)
        if organization_id:
            stmt = stmt.where(Job.organization_id == organization_id)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await db.scalar(count_stmt) or 0

        # Apply pagination and ordering
        stmt = stmt.order_by(Job.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        jobs = result.unique().scalars().all()

        # Convert to response with real-time Celery status for active jobs
        items = []
        for job in jobs:
            status = job.status
            progress = job.progress

            # For non-terminal jobs, check Celery for real-time status/progress (async to avoid blocking)
            if status not in ('completed', 'failed'):
                celery_status, celery_progress = await _get_celery_progress_async(job.celery_task_id)
                if celery_status:
                    status = celery_status
                if celery_progress:
                    progress = celery_progress

            # Extract token metrics from progress data
            token_metrics = _extract_token_metrics(job.progress)

            # Build proper progress object if we have progress data that isn't just token_metrics
            progress_obj = None
            if progress and isinstance(progress, dict):
                # Only build JobProgress if we have the required fields
                if all(k in progress for k in ('current', 'total', 'percentage')):
                    progress_obj = progress

            # Get output_type from flavor
            output_type = job.flavor.output_type if job.flavor else "text"

            # Check if flavor has extraction prompt configured
            has_extraction_prompt = bool(
                job.flavor and job.flavor.placeholder_extraction_prompt_id
            )

            # Get processing mode from flavor
            processing_mode = job.flavor.processing_mode if job.flavor else "iterative"

            items.append(JobResponse(
                id=job.id,
                service_id=job.service_id,
                service_name=job.service.name,
                flavor_id=job.flavor_id,
                flavor_name=job.flavor.name if job.flavor else "deleted",
                status=status,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                result=job.result,
                error=job.error,
                progress=progress_obj,
                organization_id=job.organization_id,
                # Fallback tracking
                fallback_applied=job.fallback_applied == "true",
                original_flavor_id=job.original_flavor_id,
                original_flavor_name=job.original_flavor_name,
                fallback_reason=job.fallback_reason,
                input_tokens=job.fallback_input_tokens,
                context_available=job.fallback_context_available,
                # Token metrics
                token_metrics=token_metrics,
                output_type=output_type,
                current_version=job.current_version,
                last_edited_at=job.last_edited_at,
                has_extraction_prompt=has_extraction_prompt,
                processing_mode=processing_mode,
                # TTL expiration
                expires_at=job.expires_at,
            ))

        return items, total

    async def cancel_job(self, db: AsyncSession, job_id: UUID) -> Optional[dict]:
        """
        Cancel a job via Celery revoke.

        Args:
            db: Database session
            job_id: Job UUID

        Returns:
            Dict with job_id, status, and message, or None if job not found
        """
        from datetime import datetime
        from app.http_server.celery_app import celery_app

        # Get job by ID
        stmt = select(Job).where(Job.id == job_id)
        result = await db.execute(stmt)
        job = result.scalar_one_or_none()

        if not job:
            return None

        # Check if job is already completed or cancelled
        if job.status in ("completed", "failed"):
            return {
                "job_id": job_id,
                "status": "failed",
                "message": f"Cannot cancel job: already {job.status}",
            }

        # Revoke the Celery task
        try:
            import asyncio
            from app.http_server.celery_app import redis_client

            # Run blocking Redis/Celery operations in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()

            # Add to revoked_tasks set in Redis for graceful cancellation
            # This allows running tasks to check and stop between batches
            await loop.run_in_executor(None, redis_client.sadd, "revoked_tasks", job.celery_task_id)
            # Set expiry on the revoked task entry (1 hour)
            await loop.run_in_executor(None, redis_client.expire, "revoked_tasks", 3600)
            logger.info(f"Added task {job.celery_task_id} to revoked_tasks set")

            # Also send Celery revoke signal (for tasks not yet started)
            await loop.run_in_executor(
                None,
                lambda: celery_app.control.revoke(job.celery_task_id, terminate=True)
            )
            logger.info(f"Revoked Celery task {job.celery_task_id} for job {job_id}")

            # Update job status
            job.status = "failed"
            job.error = "Cancelled by user"
            job.completed_at = datetime.utcnow()

            await db.commit()
            await db.refresh(job)

            return {
                "job_id": job_id,
                "status": "cancelled",
                "message": "Job cancelled successfully",
            }
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return {
                "job_id": job_id,
                "status": "failed",
                "message": f"Failed to cancel job: {str(e)}",
            }

    async def delete_job(self, db: AsyncSession, job_id: UUID) -> bool:
        """
        Delete a job and all its related data.

        Args:
            db: Database session
            job_id: UUID of the job to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        stmt = select(Job).where(Job.id == job_id)
        result = await db.execute(stmt)
        job = result.scalar_one_or_none()

        if not job:
            return False

        await db.delete(job)
        await db.commit()

        logger.info(f"Deleted job {job_id}")
        return True

    async def detect_stale_jobs(
        self,
        db: AsyncSession,
        timeout_minutes: int = DEFAULT_STALE_TIMEOUT_MINUTES,
    ) -> List[Job]:
        """
        Detect jobs stuck in active states (queued, started, processing) for too long.

        These are jobs where Celery worker died or was killed before completion.

        Args:
            db: Database session
            timeout_minutes: Minutes after which an active job is considered stale

        Returns:
            List of stale Job objects
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)

        # Find jobs in active states that haven't been updated recently
        stmt = (
            select(Job)
            .where(Job.status.in_(["queued", "started", "processing"]))
            .where(
                or_(
                    # Jobs started before cutoff
                    Job.started_at < cutoff_time,
                    # Or queued jobs created before cutoff (never started)
                    (Job.started_at.is_(None)) & (Job.created_at < cutoff_time)
                )
            )
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def detect_orphaned_jobs(
        self,
        db: AsyncSession,
    ) -> List[Job]:
        """
        Detect orphaned jobs by checking Celery task state.

        An orphaned job is one where:
        - DB status is active (queued, started, processing)
        - But Celery reports the task as UNKNOWN/PENDING (no worker processing it)
          OR Celery reports SUCCESS/FAILURE (already completed but DB not updated)

        This is more accurate than time-based detection as it checks actual Celery state.

        Args:
            db: Database session

        Returns:
            List of orphaned Job objects with their Celery status info
        """
        # Get all active jobs from database
        stmt = select(Job).where(Job.status.in_(["queued", "started", "processing"]))
        result = await db.execute(stmt)
        active_jobs = list(result.scalars().all())

        if not active_jobs:
            return []

        orphaned = []
        for job in active_jobs:
            try:
                # Check actual Celery state
                celery_status, celery_result, _ = await get_task_status_async(job.celery_task_id)

                # Job is orphaned if Celery doesn't know about it or has a terminal state
                # that wasn't synced to DB
                if celery_status in ("UNKNOWN", "SUCCESS", "FAILURE", "REVOKED"):
                    # Store celery info for logging
                    job._celery_status = celery_status
                    job._celery_result = celery_result
                    orphaned.append(job)
                    logger.debug(
                        f"Orphaned job detected: {job.id} "
                        f"(db_status={job.status}, celery_status={celery_status})"
                    )
            except Exception as e:
                logger.warning(f"Error checking Celery status for job {job.id}: {e}")
                # If we can't check Celery, treat old jobs as potentially orphaned
                cutoff = datetime.utcnow() - timedelta(minutes=DEFAULT_STALE_TIMEOUT_MINUTES)
                if job.started_at and job.started_at < cutoff:
                    job._celery_status = "CHECK_FAILED"
                    job._celery_result = None
                    orphaned.append(job)

        return orphaned

    async def cleanup_orphaned_jobs(
        self,
        db: AsyncSession,
    ) -> List[dict]:
        """
        Detect and cleanup orphaned jobs by checking Celery task state.

        This is smarter than time-based cleanup - it checks if Celery is actually
        processing the task.

        Args:
            db: Database session

        Returns:
            List of dicts with cleanup info for each job
        """
        orphaned_jobs = await self.detect_orphaned_jobs(db)

        if not orphaned_jobs:
            logger.info("No orphaned jobs detected")
            return []

        cleaned_jobs = []
        for job in orphaned_jobs:
            celery_status = getattr(job, '_celery_status', 'UNKNOWN')
            celery_result = getattr(job, '_celery_result', None)
            previous_status = job.status

            # Determine new status based on Celery state
            if celery_status == "SUCCESS":
                # Celery completed but DB wasn't updated - try to recover result
                job.status = "completed"
                if celery_result:
                    if isinstance(celery_result, dict):
                        job.result = {"output": celery_result.get("output", "")}
                    else:
                        job.result = {"output": str(celery_result)}
                job.error = None
                job.completed_at = datetime.utcnow()
                action = "recovered_success"
            elif celery_status == "FAILURE":
                # Celery failed but DB wasn't updated
                job.status = "failed"
                job.error = f"Task failed in Celery (result: {celery_result})"
                job.completed_at = datetime.utcnow()
                action = "recovered_failure"
            else:
                # UNKNOWN, REVOKED, or CHECK_FAILED - worker lost the task
                job.status = "failed"
                job.error = f"Job orphaned: Celery task state is '{celery_status}' (worker may have died)"
                job.completed_at = datetime.utcnow()
                action = "marked_orphaned"

            cleaned_jobs.append({
                "job_id": str(job.id),
                "previous_status": previous_status,
                "new_status": job.status,
                "celery_status": celery_status,
                "action": action,
                "celery_task_id": job.celery_task_id,
            })

            logger.warning(
                f"Cleaned orphaned job {job.id}: {previous_status} -> {job.status} "
                f"(celery_status={celery_status}, action={action})"
            )

        await db.commit()
        logger.info(f"Cleaned {len(cleaned_jobs)} orphaned jobs")

        return cleaned_jobs

    async def mark_stale_jobs_failed(
        self,
        db: AsyncSession,
        timeout_minutes: int = DEFAULT_STALE_TIMEOUT_MINUTES,
    ) -> List[dict]:
        """
        Detect and mark stale jobs as failed.

        This should be called on startup and can be triggered via API.

        Args:
            db: Database session
            timeout_minutes: Minutes after which an active job is considered stale

        Returns:
            List of dicts with job_id and previous_status for each marked job
        """
        stale_jobs = await self.detect_stale_jobs(db, timeout_minutes)

        if not stale_jobs:
            logger.info("No stale jobs detected")
            return []

        marked_jobs = []
        for job in stale_jobs:
            previous_status = job.status
            job.status = "failed"
            job.error = f"Job marked as failed: stale after {timeout_minutes} minutes in '{previous_status}' state (worker may have died)"
            job.completed_at = datetime.utcnow()

            marked_jobs.append({
                "job_id": str(job.id),
                "previous_status": previous_status,
                "celery_task_id": job.celery_task_id,
            })

            logger.warning(
                f"Marked stale job {job.id} as failed "
                f"(was '{previous_status}', celery_task_id={job.celery_task_id})"
            )

        await db.commit()
        logger.info(f"Marked {len(marked_jobs)} stale jobs as failed")

        return marked_jobs

    async def get_active_job_count(self, db: AsyncSession) -> int:
        """Get count of jobs in active (non-terminal) states."""
        stmt = select(func.count()).select_from(Job).where(
            Job.status.in_(["queued", "started", "processing"])
        )
        return await db.scalar(stmt) or 0

    async def cleanup_expired_jobs(self, db: AsyncSession) -> int:
        """
        Delete jobs that have exceeded their TTL (expires_at in the past).

        Jobs with NULL expires_at are never deleted.

        Args:
            db: Database session

        Returns:
            Number of deleted jobs
        """
        # Find expired jobs
        stmt = select(Job).where(
            Job.expires_at.isnot(None),
            Job.expires_at < datetime.utcnow()
        )
        result = await db.execute(stmt)
        expired_jobs = result.scalars().all()

        if not expired_jobs:
            return 0

        # Delete them
        for job in expired_jobs:
            await db.delete(job)

        await db.commit()
        logger.info(f"Deleted {len(expired_jobs)} expired jobs (TTL cleanup)")

        return len(expired_jobs)


job_service = JobService()
