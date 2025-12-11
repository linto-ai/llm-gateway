"""Service for managing job result version history."""
import json
import logging
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.job import Job
from app.models.job_result_version import JobResultVersion
from app.schemas.job import JobVersionSummary, JobVersionDetail

logger = logging.getLogger(__name__)

# Configuration constants
MAX_VERSIONS = 10


class JobResultVersionService:
    """Service for job result version management.

    Stores full content for each version (no diffs) for simplicity and reliability.
    """

    def _extract_result_content(self, result) -> str:
        """Extract the text content from a job result.

        Job results can be stored as:
        - dict with 'output' key
        - plain string
        - other structures
        """
        if result is None:
            return ""
        if isinstance(result, dict):
            if "output" in result:
                return str(result["output"])
            return json.dumps(result)
        return str(result)

    async def _get_job_with_versions(
        self, db: AsyncSession, job_id: UUID
    ) -> Optional[Job]:
        """Get job with its versions preloaded."""
        stmt = (
            select(Job)
            .options(joinedload(Job.versions))
            .where(Job.id == job_id)
        )
        result = await db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def create_initial_version(
        self,
        db: AsyncSession,
        job_id: UUID,
        content: str,
        created_by: Optional[str] = None,
    ) -> Optional[JobResultVersion]:
        """Create version 1 for a newly completed job.

        Stores the original result as full content.
        """
        version = JobResultVersion(
            job_id=job_id,
            version_number=1,
            diff="",  # Not used anymore, kept for DB compatibility
            full_content=content,
            created_by=created_by,
        )
        db.add(version)
        await db.flush()
        return version

    async def create_version(
        self,
        db: AsyncSession,
        job_id: UUID,
        new_content: str,
        created_by: Optional[str] = None,
    ) -> Optional[JobResultVersion]:
        """Create a new version with full content storage.

        Args:
            db: Database session
            job_id: Job UUID
            new_content: The new result content
            created_by: Optional user identifier

        Returns:
            The new version, or None if job not found
        """
        job = await self._get_job_with_versions(db, job_id)
        if not job:
            return None

        # Get current version content
        current_content = self._extract_result_content(job.result)
        current_version = job.current_version

        # If this is the first edit (no versions exist yet), create version 1 first
        # to preserve the original content
        if not job.versions and current_version == 1:
            logger.info(f"Creating initial version 1 for job {job_id}")
            await self.create_initial_version(
                db, job_id, current_content, created_by="system"
            )

        # Compute next version number
        next_version = current_version + 1

        # Create the new version with full content (no diffs)
        version = JobResultVersion(
            job_id=job_id,
            version_number=next_version,
            diff="",  # Not used anymore, kept for DB compatibility
            full_content=new_content,
            created_by=created_by,
        )
        db.add(version)

        # Update job with new content and version, preserving other fields (metadata, etc.)
        if isinstance(job.result, dict):
            job.result = {**job.result, "output": new_content}
        else:
            job.result = {"output": new_content}
        job.current_version = next_version
        job.last_edited_at = datetime.utcnow()

        await db.flush()

        # Cleanup old versions (but keep version 1)
        await self._cleanup_old_versions(db, job_id)

        return version

    async def _cleanup_old_versions(
        self, db: AsyncSession, job_id: UUID
    ) -> None:
        """Remove versions beyond MAX_VERSIONS limit.

        Always preserves version 1 (original).
        """
        # Get all versions ordered by version_number
        stmt = (
            select(JobResultVersion)
            .where(JobResultVersion.job_id == job_id)
            .order_by(JobResultVersion.version_number.desc())
        )
        result = await db.execute(stmt)
        versions = result.scalars().all()

        if len(versions) <= MAX_VERSIONS:
            return

        # Identify versions to delete (oldest first, but never version 1)
        versions_to_delete = []
        for v in reversed(versions):  # Oldest first
            if len(versions) - len(versions_to_delete) <= MAX_VERSIONS:
                break
            if v.version_number != 1:
                versions_to_delete.append(v.id)

        if versions_to_delete:
            delete_stmt = delete(JobResultVersion).where(
                JobResultVersion.id.in_(versions_to_delete)
            )
            await db.execute(delete_stmt)
            logger.info(
                f"Deleted {len(versions_to_delete)} old versions for job {job_id}"
            )

    async def list_versions(
        self, db: AsyncSession, job_id: UUID
    ) -> Optional[List[JobVersionSummary]]:
        """List version summaries for a job.

        Returns None if job doesn't exist.
        """
        job = await self._get_job_with_versions(db, job_id)
        if not job:
            return None

        # If no versions exist, return current state as version 1
        if not job.versions:
            current_content = self._extract_result_content(job.result)
            return [
                JobVersionSummary(
                    version_number=1,
                    created_at=job.completed_at or job.created_at,
                    created_by=None,
                    content_length=len(current_content),
                )
            ]

        summaries = []
        for v in sorted(job.versions, key=lambda x: x.version_number):
            content_length = len(v.full_content) if v.full_content else 0
            summaries.append(
                JobVersionSummary(
                    version_number=v.version_number,
                    created_at=v.created_at,
                    created_by=v.created_by,
                    content_length=content_length,
                )
            )

        return summaries

    async def get_version(
        self, db: AsyncSession, job_id: UUID, version_number: int
    ) -> Optional[JobVersionDetail]:
        """Get full details for a specific version.

        Returns the full content directly (no reconstruction needed).
        """
        job = await self._get_job_with_versions(db, job_id)
        if not job:
            return None

        # If no versions stored and requesting version 1, return current result
        if not job.versions and version_number == 1:
            content = self._extract_result_content(job.result)
            return JobVersionDetail(
                version_number=1,
                created_at=job.completed_at or job.created_at,
                created_by=None,
                content=content,
            )

        # Find the requested version
        version = None
        for v in job.versions:
            if v.version_number == version_number:
                version = v
                break

        if not version:
            return None

        # Return full content directly
        return JobVersionDetail(
            version_number=version.version_number,
            created_at=version.created_at,
            created_by=version.created_by,
            content=version.full_content or "",
        )

    async def restore_version(
        self,
        db: AsyncSession,
        job_id: UUID,
        version_number: int,
        created_by: Optional[str] = None,
    ) -> Optional[Job]:
        """Restore job to a previous version.

        Creates a new version entry with the restored content.

        Args:
            db: Database session
            job_id: Job UUID
            version_number: Version to restore
            created_by: Optional user identifier

        Returns:
            Updated job, or None if job/version not found
        """
        job = await self._get_job_with_versions(db, job_id)
        if not job:
            return None

        # Cannot restore to current version
        if version_number == job.current_version:
            return None

        # Get the content of the version to restore
        version_detail = await self.get_version(db, job_id, version_number)
        if not version_detail:
            return None

        # Create a new version with the restored content
        await self.create_version(db, job_id, version_detail.content, created_by)

        # Refresh job to get updated state
        await db.refresh(job)
        return job


# Singleton instance
job_result_version_service = JobResultVersionService()
