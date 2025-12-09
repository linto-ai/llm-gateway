#!/usr/bin/env python3
"""Metadata extraction service for extracting structured data from job results."""
import json
import logging
import re
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.service_flavor import ServiceFlavor
from app.models.prompt import Prompt
from app.services.document_template_service import document_template_service
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)


class MetadataExtractionService:
    """Service for extracting metadata from job results using LLM."""

    # Fallback fields if no templates are configured
    DEFAULT_FIELDS = [
        "title",
        "summary",
        "participants",
        "date",
        "topics",
        "action_items",
        "sentiment",
        "language",
        "word_count",
        "key_points",
    ]

    def __init__(self, llm_inference=None):
        """
        Initialize metadata extraction service.

        Args:
            llm_inference: Optional LLM inference engine for extraction
        """
        self.llm = llm_inference

    async def _get_all_template_placeholders(
        self,
        db: AsyncSession,
        service_id: UUID,
    ) -> List[str]:
        """
        Collect all unique placeholders from ALL templates attached to a service.

        This ensures metadata extraction covers all fields that might be needed
        regardless of which template is used for export.

        Args:
            db: Database session
            service_id: Service ID to get templates for

        Returns:
            Sorted list of unique placeholder names from all templates
        """
        templates = await document_template_service.list_templates(
            db, service_id=service_id
        )

        # Always start with default fields
        all_placeholders = set(self.DEFAULT_FIELDS)

        # Add placeholders from all templates (no duplicates thanks to set)
        for template in templates:
            if template.placeholders:
                all_placeholders.update(template.placeholders)

        # Remove standard placeholders - these are provided by the system, not extracted
        standard_placeholders = set(DocumentService.STANDARD_PLACEHOLDERS)
        all_placeholders -= standard_placeholders

        return sorted(list(all_placeholders))

    async def extract_metadata(
        self,
        db: AsyncSession,
        job: Job,
        flavor: ServiceFlavor,
    ) -> Dict[str, Any]:
        """
        Extract metadata from job result using the flavor's extraction prompt.

        Args:
            db: Database session
            job: Job with result to extract from
            flavor: ServiceFlavor with extraction configuration

        Returns:
            Dict of extracted metadata
        """
        if not flavor.placeholder_extraction_prompt_id:
            return {}

        # Get extraction prompt
        prompt = await db.get(Prompt, flavor.placeholder_extraction_prompt_id)
        if not prompt:
            logger.warning(f"Extraction prompt {flavor.placeholder_extraction_prompt_id} not found")
            return {}

        # Get job result content
        result_content = self._get_result_content(job)
        if not result_content:
            return {}

        # Build extraction prompt with placeholders
        # Get ALL placeholders from ALL templates for this service
        fields_to_extract = await self._get_all_template_placeholders(db, job.service_id)
        logger.info(f"Extracting metadata fields for service {job.service_id}: {fields_to_extract}")
        extraction_prompt = prompt.content.replace(
            "{{output}}", result_content
        ).replace(
            "{{metadata_fields}}", json.dumps(fields_to_extract)
        )

        # Call LLM for extraction
        try:
            if not self.llm:
                logger.warning("No LLM configured for metadata extraction")
                return {"_extraction_error": "No LLM configured"}

            response = await self.llm.generate(
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=2000
            )

            # Parse JSON response
            metadata = self._parse_json_response(response)

            # Filter to requested field names (extract field name before colon if present)
            if fields_to_extract:
                valid_keys = set()
                for f in fields_to_extract:
                    field_name = f.split(":")[0].strip()
                    valid_keys.add(field_name)
                metadata = {k: v for k, v in metadata.items() if k in valid_keys}

            return metadata

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction response as JSON: {e}")
            return {"_extraction_error": f"JSON parse error: {str(e)}"}
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return {"_extraction_error": str(e)}

    async def extract_with_prompt(
        self,
        db: AsyncSession,
        job: Job,
        prompt_id: UUID,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract metadata using a specific prompt (for manual extraction).

        Args:
            db: Database session
            job: Job to extract from
            prompt_id: ID of extraction prompt to use
            fields: Optional list of fields to extract

        Returns:
            Dict of extracted metadata

        Raises:
            ValueError: If prompt not found
        """
        prompt = await db.get(Prompt, prompt_id)
        if not prompt:
            raise ValueError("Extraction prompt not found")

        result_content = self._get_result_content(job)
        if not result_content:
            return {}

        # Use provided fields, or get ALL placeholders from ALL templates for this service
        if fields:
            fields_to_extract = fields
        else:
            fields_to_extract = await self._get_all_template_placeholders(db, job.service_id)

        # Build extraction prompt - handle both {} and {{}} placeholder styles
        extraction_prompt = prompt.content

        # Find positions of {} placeholders (not part of {{}})
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
            extraction_prompt = extraction_prompt[:pos2] + json.dumps(fields_to_extract) + extraction_prompt[pos2+2:]
            pos1 = placeholder_positions[-2]
            extraction_prompt = extraction_prompt[:pos1] + result_content + extraction_prompt[pos1+2:]
        else:
            # Fallback to {{placeholder}} style
            extraction_prompt = extraction_prompt.replace("{{output}}", result_content)
            extraction_prompt = extraction_prompt.replace("{{metadata_fields}}", json.dumps(fields_to_extract))

        if not self.llm:
            raise ValueError("No LLM configured for metadata extraction")

        response = await self.llm.generate(
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0.1,
            max_tokens=2000
        )

        metadata = self._parse_json_response(response)

        # Filter to requested field names (extract field name before colon if present)
        if fields_to_extract:
            valid_keys = set()
            for f in fields_to_extract:
                field_name = f.split(":")[0].strip()
                valid_keys.add(field_name)
            metadata = {k: v for k, v in metadata.items() if k in valid_keys}

        return metadata

    async def update_job_metadata(
        self,
        db: AsyncSession,
        job_id: UUID,
        metadata: Dict[str, Any]
    ) -> Optional[Job]:
        """
        Update job with extracted metadata.

        Stores metadata in result.extracted_metadata (consolidated JSONB structure).

        Args:
            db: Database session
            job_id: Job to update
            metadata: Extracted metadata

        Returns:
            Updated Job or None if not found
        """
        job = await db.get(Job, job_id)
        if job:
            # Update result JSONB with extracted_metadata
            # Create a new dict to ensure SQLAlchemy detects the change
            current_result = dict(job.result) if job.result else {}
            current_result["extracted_metadata"] = metadata
            job.result = current_result
            # Force SQLAlchemy to detect the JSONB change
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(job, "result")
            await db.flush()
            await db.refresh(job)
        return job

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
        text = response.strip()

        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```) and last line (```)
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            text = "\n".join(lines)

        # Also try to extract JSON from within the text if it's wrapped
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            text = json_match.group()

        return json.loads(text)


# Factory function to create service with LLM
def get_metadata_extraction_service(llm_inference=None) -> MetadataExtractionService:
    """Get metadata extraction service instance."""
    return MetadataExtractionService(llm_inference)
