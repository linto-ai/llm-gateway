#!/usr/bin/env python3
"""Export service for just-in-time extraction and document export."""
import json
import logging
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.document_template import DocumentTemplate
from app.models.job import Job
from app.models.prompt import Prompt
from app.services.document_service import DocumentService
from app.services.document_template_service import DocumentTemplateService

logger = logging.getLogger(__name__)


class ExportService:
    """Service for just-in-time extraction and document export.

    Handles the workflow:
    1. Load template (specified or default)
    2. Parse template placeholders
    3. Check which placeholders are already in job.result.extracted_metadata
    4. If missing placeholders exist AND flavor has extraction prompt configured:
       - Perform just-in-time extraction for missing fields only
       - Update job.result.extracted_metadata with new values
       - Record extraction in job token metrics
    5. Generate document with all available placeholder values
    """

    def __init__(
        self,
        document_service: Optional[DocumentService] = None,
        template_service: Optional[DocumentTemplateService] = None,
    ):
        """Initialize export service.

        Args:
            document_service: DocumentService instance (uses singleton if not provided)
            template_service: DocumentTemplateService instance (uses singleton if not provided)
        """
        from app.services.document_service import document_service as ds_singleton
        from app.services.document_template_service import document_template_service as dts_singleton

        self.document_service = document_service or ds_singleton
        self.template_service = template_service or dts_singleton

    async def export_with_extraction(
        self,
        db: AsyncSession,
        job: Job,
        template: Optional[DocumentTemplate],
        format: str,
        llm_inference=None,
        version_number: Optional[int] = None,
    ) -> BytesIO | str:
        """
        Export job with just-in-time metadata extraction.

        Args:
            db: Database session
            job: Job to export
            template: Template to use (None uses built-in default)
            format: Export format ('docx', 'pdf', or 'html')
            llm_inference: Optional LLM inference engine for extraction
            version_number: Optional version number (fetches content from DB, uses per-version extraction cache)

        Returns:
            BytesIO containing the generated document (docx/pdf), or HTML string (html)
        """
        # Get template placeholders and ID
        template_placeholders = []
        template_id = None
        if template:
            template_id = str(template.id)
            if template.placeholders:
                template_placeholders = template.placeholders

        # Determine content and metadata based on version
        version_content = None
        force_extraction = False  # Force extraction for new versions without cache

        if version_number is not None:
            # Fetch version content from database
            version_content = await self._get_version_content(db, job.id, version_number)
            if version_content:
                # Per-version extraction: check cache first
                current_metadata = self._get_version_metadata(job, version_number)
                last_extraction_template_id = self._get_version_template_id(job, version_number)

                # If no cached metadata for this version, force extraction using same fields as main metadata
                if not current_metadata:
                    main_metadata = self._get_current_metadata(job)
                    if main_metadata:
                        # Use the same field names from main metadata as placeholders to extract
                        template_placeholders = list(main_metadata.keys())
                        force_extraction = True
                        logger.info(f"No cached metadata for version {version_number}, will extract fields: {template_placeholders}")
            else:
                logger.warning(f"Version {version_number} not found for job {job.id}, using current content")
                current_metadata = self._get_current_metadata(job)
                last_extraction_template_id = job.result.get("_extraction_template_id") if job.result else None
        else:
            # Default: use main job metadata
            current_metadata = self._get_current_metadata(job)
            last_extraction_template_id = None
            if job.result and isinstance(job.result, dict):
                last_extraction_template_id = job.result.get("_extraction_template_id")

        # Find missing placeholders (considers template change)
        missing = self._get_missing_placeholders(
            template_placeholders,
            current_metadata,
            template_id=template_id,
            last_extraction_template_id=last_extraction_template_id,
        )

        # Perform just-in-time extraction if needed (or forced for new versions)
        if (missing or force_extraction) and llm_inference and self._can_extract(db, job):
            # Use version content for extraction if available
            extraction_content = version_content if version_content else None
            logger.info(f"JIT extraction starting for job {job.id}, version={version_number}, template={template_id}, missing={len(missing)} fields")
            try:
                new_metadata = await self._extract_metadata(
                    db, job, missing, llm_inference,
                    content_override=extraction_content
                )
                if new_metadata:
                    if version_number is not None and version_content:
                        # Cache extraction for this specific version
                        await self._update_version_metadata(db, job, version_number, new_metadata, template_id=template_id)
                    else:
                        # Update main job metadata
                        await self._update_job_metadata(db, job, new_metadata, template_id=template_id)
                    logger.info(f"JIT extraction completed for job {job.id}, version={version_number}, extracted: {list(new_metadata.keys())}")
            except Exception as e:
                logger.error(f"JIT extraction failed for job {job.id}: {e}")
                # Continue with export even if extraction fails

        # Get version-specific metadata for document generation
        version_metadata = None
        if version_number is not None and version_content:
            version_metadata = self._get_version_metadata(job, version_number)

        # Generate document
        if format == "docx":
            return await self.document_service.generate_docx(job, template, version_content=version_content, version_metadata=version_metadata)
        elif format == "html":
            return await self.document_service.generate_html(job, template, version_content=version_content, version_metadata=version_metadata)
        else:
            return await self.document_service.generate_pdf(job, template, version_content=version_content, version_metadata=version_metadata)

    async def get_export_preview(
        self,
        db: AsyncSession,
        job: Job,
        template: Optional[DocumentTemplate],
    ) -> Dict[str, Any]:
        """
        Get preview of export showing placeholder status.

        Args:
            db: Database session
            job: Job to preview
            template: Template to use

        Returns:
            Dict with template_id, template_name, placeholders status, extraction_required
        """
        template_placeholders = []
        template_id = None
        template_name = "Built-in Default"

        if template:
            template_id = str(template.id)
            template_name = template.name_fr
            if template.placeholders:
                template_placeholders = template.placeholders

        current_metadata = self._get_current_metadata(job)
        can_extract = await self._can_extract_async(db, job)

        # Check if template changed since last extraction
        last_extraction_template_id = None
        if job.result and isinstance(job.result, dict):
            last_extraction_template_id = job.result.get("_extraction_template_id")

        template_changed = (
            template_id is not None
            and last_extraction_template_id is not None
            and template_id != last_extraction_template_id
        )

        # Bootstrap: if we have extracted_metadata but no template tracking yet
        needs_bootstrap = (
            template_id is not None
            and last_extraction_template_id is None
            and len(current_metadata) > 0
        )

        placeholders_status = []
        extraction_required = False

        for placeholder in template_placeholders:
            # Parse placeholder name (handle "name: description" format)
            info = self.template_service.parse_placeholder_info(placeholder)
            name = info["name"]

            if info["is_standard"]:
                # Standard placeholders are always available
                placeholders_status.append({
                    "name": name,
                    "status": "available",
                    "value": self._get_standard_placeholder_value(job, name),
                })
            elif (template_changed or needs_bootstrap) and can_extract:
                # Template changed - need to re-extract all non-standard placeholders
                placeholders_status.append({
                    "name": name,
                    "status": "extraction_required",
                    "value": None,
                })
                extraction_required = True
            elif name in current_metadata and current_metadata.get(name) is not None:
                # Already extracted with valid value
                value = current_metadata[name]
                if isinstance(value, (list, dict)):
                    value = json.dumps(value, ensure_ascii=False)
                placeholders_status.append({
                    "name": name,
                    "status": "available",
                    "value": str(value)[:100] if value else None,  # Preview truncated
                })
            elif can_extract:
                # Can be extracted (missing or null)
                placeholders_status.append({
                    "name": name,
                    "status": "extraction_required",
                    "value": None,
                })
                extraction_required = True
            else:
                # Missing and cannot be extracted
                placeholders_status.append({
                    "name": name,
                    "status": "missing",
                    "value": None,
                })

        # Estimate extraction tokens (rough estimate based on job result size)
        estimated_tokens = None
        if extraction_required:
            result_content = self._get_result_content(job)
            if result_content:
                # Rough estimate: ~4 chars per token
                estimated_tokens = len(result_content) // 4

        return {
            "template_id": template_id,
            "template_name": template_name,
            "placeholders": placeholders_status,
            "extraction_required": extraction_required,
            "estimated_extraction_tokens": estimated_tokens,
            "template_changed": template_changed,
        }

    def _get_current_metadata(self, job: Job) -> Dict[str, Any]:
        """Get current extracted metadata from job result."""
        if not job.result or not isinstance(job.result, dict):
            return {}
        return job.result.get("extracted_metadata", {})

    async def _get_version_content(self, db: AsyncSession, job_id: UUID, version_number: int) -> Optional[str]:
        """Fetch full content for a specific version from the database."""
        from sqlalchemy import select
        from app.models.job_result_version import JobResultVersion

        stmt = select(JobResultVersion).where(
            JobResultVersion.job_id == job_id,
            JobResultVersion.version_number == version_number
        )
        result = await db.execute(stmt)
        version = result.scalar_one_or_none()

        if version and version.full_content:
            return version.full_content
        return None

    def _get_version_metadata(self, job: Job, version_number: int) -> Dict[str, Any]:
        """Get cached extracted metadata for a specific version."""
        if not job.result or not isinstance(job.result, dict):
            return {}
        version_extractions = job.result.get("version_extractions", {})
        version_key = str(version_number)
        if version_key in version_extractions:
            return version_extractions[version_key].get("metadata", {})
        return {}

    def _get_version_template_id(self, job: Job, version_number: int) -> Optional[str]:
        """Get the template ID used for a specific version's extraction."""
        if not job.result or not isinstance(job.result, dict):
            return None
        version_extractions = job.result.get("version_extractions", {})
        version_key = str(version_number)
        if version_key in version_extractions:
            return version_extractions[version_key].get("template_id")
        return None

    async def _update_version_metadata(
        self,
        db: AsyncSession,
        job: Job,
        version_number: int,
        metadata: Dict[str, Any],
        template_id: Optional[str] = None,
    ) -> None:
        """
        Cache extracted metadata for a specific version.

        Stores in job.result.version_extractions[version_number].
        """
        result = dict(job.result) if job.result else {}

        # Initialize version_extractions if needed
        if "version_extractions" not in result:
            result["version_extractions"] = {}

        version_key = str(version_number)
        result["version_extractions"][version_key] = {
            "metadata": metadata,
            "template_id": template_id,
            "extracted_at": datetime.utcnow().isoformat(),
        }

        job.result = result
        flag_modified(job, "result")
        await db.flush()

    def _get_missing_placeholders(
        self,
        template_placeholders: List[str],
        current_metadata: Dict[str, Any],
        template_id: Optional[str] = None,
        last_extraction_template_id: Optional[str] = None,
    ) -> List[str]:
        """
        Find placeholders that need extraction.

        Args:
            template_placeholders: Placeholders defined in template
            current_metadata: Already extracted metadata
            template_id: Current template ID being used for export
            last_extraction_template_id: Template ID used for last extraction

        Returns:
            List of placeholder names that need extraction
        """
        missing = []
        standard_placeholders = set(DocumentTemplateService.STANDARD_PLACEHOLDERS)

        # If template changed since last extraction, force re-extraction of all non-standard placeholders
        # Also force re-extraction if we have metadata but no tracking yet (bootstrap)
        template_changed = (
            template_id is not None
            and last_extraction_template_id is not None
            and template_id != last_extraction_template_id
        )

        # Bootstrap: if we have extracted_metadata but no template tracking yet,
        # force re-extraction to establish proper template tracking
        needs_bootstrap = (
            template_id is not None
            and last_extraction_template_id is None
            and len(current_metadata) > 0
        )

        for placeholder in template_placeholders:
            # Parse placeholder name
            info = self.template_service.parse_placeholder_info(placeholder)
            name = info["name"]

            # Skip standard placeholders (system-provided)
            if name in standard_placeholders:
                continue

            # Only extract if the value doesn't exist in current_metadata
            # Null values are valid extraction results - LLM tried but couldn't extract
            if name not in current_metadata:
                missing.append(placeholder)

        return missing

    async def _can_extract_async(self, db: AsyncSession, job: Job) -> bool:
        """Check if extraction is possible for this job (async version)."""
        # Need job flavor with extraction prompt
        if not job.flavor_id:
            return False

        # Load flavor if needed
        from app.models.service_flavor import ServiceFlavor
        from sqlalchemy import select

        result = await db.execute(
            select(ServiceFlavor).where(ServiceFlavor.id == job.flavor_id)
        )
        flavor = result.scalar_one_or_none()

        if not flavor or not flavor.placeholder_extraction_prompt_id:
            return False

        return True

    def _can_extract(self, db: AsyncSession, job: Job) -> bool:
        """Check if extraction is possible (sync check based on job data)."""
        # Basic check - actual capability depends on flavor config
        return job.flavor_id is not None

    async def _extract_metadata(
        self,
        db: AsyncSession,
        job: Job,
        missing_fields: List[str],
        llm_inference,
        content_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform just-in-time extraction for missing fields.

        Args:
            db: Database session
            job: Job to extract from
            missing_fields: List of field names/placeholders to extract
            llm_inference: LLM inference engine
            content_override: Optional content to extract from (instead of job result)

        Returns:
            Dict of extracted metadata
        """
        from app.models.service_flavor import ServiceFlavor
        from sqlalchemy import select

        # Get flavor with extraction prompt
        result = await db.execute(
            select(ServiceFlavor).where(ServiceFlavor.id == job.flavor_id)
        )
        flavor = result.scalar_one_or_none()

        if not flavor or not flavor.placeholder_extraction_prompt_id:
            return {}

        # Get extraction prompt
        prompt = await db.get(Prompt, flavor.placeholder_extraction_prompt_id)
        if not prompt:
            logger.warning(f"Extraction prompt {flavor.placeholder_extraction_prompt_id} not found")
            return {}

        # Use content_override if provided, otherwise get from job result
        result_content = content_override if content_override else self._get_result_content(job)
        if not result_content:
            return {}

        # Parse field names from placeholders (handle "name: description" format)
        # Keep both: full placeholders (with descriptions) for the LLM prompt,
        # and just names for filtering the response
        field_names = []
        field_descriptions = []  # Full placeholder strings with descriptions
        for placeholder in missing_fields:
            info = self.template_service.parse_placeholder_info(placeholder)
            field_names.append(info["name"])
            # Keep the full placeholder string (name: description) for the LLM
            field_descriptions.append(placeholder)

        # Build extraction prompt - pass full descriptions so LLM knows context/defaults
        extraction_prompt = prompt.content.replace(
            "{{output}}", result_content
        ).replace(
            "{{metadata_fields}}", json.dumps(field_descriptions)
        )

        # Also handle {} style placeholders
        import re
        placeholder_positions = []
        i = 0
        while i < len(extraction_prompt):
            if extraction_prompt[i:i+2] == "{}":
                placeholder_positions.append(i)
                i += 2
            else:
                i += 1

        if len(placeholder_positions) >= 2:
            # Replace from end to avoid position shifts
            pos2 = placeholder_positions[-1]
            extraction_prompt = extraction_prompt[:pos2] + json.dumps(field_descriptions) + extraction_prompt[pos2+2:]
            pos1 = placeholder_positions[-2]
            extraction_prompt = extraction_prompt[:pos1] + result_content + extraction_prompt[pos1+2:]

        # Call LLM for extraction
        try:
            start_time = datetime.utcnow()

            response = await llm_inference.generate(
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.1,
                max_tokens=2000
            )

            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.info(f"JIT extraction LLM response ({len(response)} chars): {response[:500]}...")

            # Parse JSON response
            metadata = self._parse_json_response(response)
            logger.info(f"JIT extraction parsed metadata: {metadata}")

            # Filter to requested fields only
            if field_names:
                metadata = {k: v for k, v in metadata.items() if k in field_names}
                logger.info(f"JIT extraction filtered to {len(metadata)} fields: {list(metadata.keys())}")

            # Record extraction tokens (rough estimate)
            prompt_tokens = len(extraction_prompt) // 4
            completion_tokens = len(response) // 4

            await self._record_extraction_tokens(
                db, job, prompt_tokens, completion_tokens, duration_ms
            )

            return metadata

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction response as JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"JIT extraction failed: {e}")
            return {}

    async def _update_job_metadata(
        self,
        db: AsyncSession,
        job: Job,
        new_metadata: Dict[str, Any],
        template_id: Optional[str] = None,
    ) -> None:
        """
        Update job result with new extracted metadata.

        Args:
            db: Database session
            job: Job to update
            new_metadata: New metadata to merge
            template_id: Template ID used for this extraction (for tracking)
        """
        logger.info(f"_update_job_metadata called with {len(new_metadata)} new fields: {list(new_metadata.keys())}")

        # Get current result
        result = dict(job.result) if job.result else {}

        # Merge metadata
        current_metadata = result.get("extracted_metadata", {})
        logger.info(f"Current metadata before merge: {list(current_metadata.keys())}")
        current_metadata.update(new_metadata)
        result["extracted_metadata"] = current_metadata
        logger.info(f"Metadata after merge: {current_metadata}")

        # Track which template was used for extraction
        if template_id:
            result["_extraction_template_id"] = template_id

        # Update job
        job.result = result
        flag_modified(job, "result")
        await db.flush()

    async def _record_extraction_tokens(
        self,
        db: AsyncSession,
        job: Job,
        prompt_tokens: int,
        completion_tokens: int,
        duration_ms: int,
    ) -> None:
        """
        Record extraction token usage in job result and progress.

        Args:
            db: Database session
            job: Job to update
            prompt_tokens: Prompt token count
            completion_tokens: Completion token count
            duration_ms: Duration in milliseconds
        """
        now = datetime.utcnow()
        total_tokens = prompt_tokens + completion_tokens

        # Add extraction tracking to result._extractions
        result = dict(job.result) if job.result else {}
        extractions = result.get("_extractions", [])
        extractions.append({
            "timestamp": now.isoformat(),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "duration_ms": duration_ms,
            "type": "just_in_time",
        })
        result["_extractions"] = extractions
        job.result = result
        flag_modified(job, "result")

        # Also add to progress.token_metrics.passes for timeline display
        progress = dict(job.progress) if job.progress else {}
        token_metrics = progress.get("token_metrics", {})
        passes = token_metrics.get("passes", [])

        # Determine pass number
        pass_number = len(passes) + 1

        # Add JIT extraction pass
        started_at = now - timedelta(milliseconds=duration_ms)
        passes.append({
            "pass_number": pass_number,
            "pass_type": "extraction",
            "started_at": started_at.isoformat(),
            "completed_at": now.isoformat(),
            "duration_ms": duration_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "input_chars": 0,  # Not tracked for JIT
            "output_chars": 0,  # Not tracked for JIT
            "estimated_cost": None,
        })

        # Update totals
        token_metrics["passes"] = passes
        token_metrics["total_tokens"] = token_metrics.get("total_tokens", 0) + total_tokens
        token_metrics["total_prompt_tokens"] = token_metrics.get("total_prompt_tokens", 0) + prompt_tokens
        token_metrics["total_completion_tokens"] = token_metrics.get("total_completion_tokens", 0) + completion_tokens
        token_metrics["total_duration_ms"] = token_metrics.get("total_duration_ms", 0) + duration_ms

        # Recalculate averages
        num_passes = len(passes)
        if num_passes > 0:
            token_metrics["avg_tokens_per_pass"] = token_metrics["total_tokens"] / num_passes
            token_metrics["avg_duration_per_pass_ms"] = token_metrics["total_duration_ms"] / num_passes

        progress["token_metrics"] = token_metrics
        job.progress = progress
        flag_modified(job, "progress")

    def _get_result_content(self, job: Job) -> Optional[str]:
        """Extract text content from job result."""
        if not job.result:
            return None

        if isinstance(job.result, str):
            return job.result
        elif isinstance(job.result, dict):
            return (
                job.result.get("content")
                or job.result.get("text")
                or job.result.get("output")
                or json.dumps(job.result, ensure_ascii=False)
            )
        return str(job.result)

    def _get_standard_placeholder_value(self, job: Job, name: str) -> Optional[str]:
        """Get value for a standard placeholder."""
        if name == "output":
            content = self._get_result_content(job)
            return content[:100] if content else None  # Preview only
        elif name == "job_id":
            return str(job.id)
        elif name == "job_date":
            return job.completed_at.strftime("%Y-%m-%d") if job.completed_at else None
        elif name == "service_name":
            return job.service.name if job.service else None
        elif name == "flavor_name":
            return job.flavor.name if job.flavor else None
        elif name == "organization_name":
            return job.organization_id
        elif name == "generated_at":
            return datetime.now().strftime("%Y-%m-%d %H:%M")
        return None

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling markdown code blocks.

        Args:
            response: LLM response string

        Returns:
            Parsed JSON dict

        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        import re

        text = response.strip()

        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            text = "\n".join(lines)

        # Try to extract JSON from within the text
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            text = json_match.group()

        return json.loads(text)


# Factory function
def get_export_service() -> ExportService:
    """Get export service instance."""
    return ExportService()


# Singleton instance
export_service = ExportService()
