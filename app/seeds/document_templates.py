#!/usr/bin/env python3
"""Seed global document templates from templates/default/ directory."""
import logging
import shutil
import uuid as uuid_lib
from pathlib import Path
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document_template import DocumentTemplate
from app.services.document_template_service import document_template_service

logger = logging.getLogger(__name__)

# Source directory for default templates (in repo)
SOURCE_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "default"

# Global templates to seed
GLOBAL_TEMPLATES: List[Dict[str, Any]] = [
    {
        "file_name": "basic-report.docx",
        "name": "Basic Report",
        "description": "General-purpose report template with title, summary, and content sections. Suitable for any service type.",
    },
    {
        "file_name": "meeting-summary.docx",
        "name": "Meeting Summary",
        "description": "Meeting notes template with participants, date, agenda, and action items. Ideal for summarization services.",
    },
    {
        "file_name": "extraction-test.docx",
        "name": "Extraction Report",
        "description": "Template for metadata extraction results with dynamic placeholders for extracted fields.",
    },
    {
        "file_name": "silly-extraction-test.docx",
        "name": "Silly Extraction Test",
        "description": "Test template with whimsical placeholders for extraction testing and demonstration purposes.",
    },
]


async def seed_global_templates(db: AsyncSession) -> Dict[str, int]:
    """
    Seed global document templates from templates/default/ directory.

    Global templates have service_id=NULL and can be imported into any service.

    Args:
        db: Database session

    Returns:
        Dict with counts of created templates
    """
    stats = {"templates_created": 0, "templates_skipped": 0}

    if not SOURCE_TEMPLATES_DIR.exists():
        logger.warning(f"Source templates directory not found: {SOURCE_TEMPLATES_DIR}")
        return stats

    # Ensure global templates directory exists
    global_dir = document_template_service.TEMPLATES_DIR / "global"
    global_dir.mkdir(parents=True, exist_ok=True)

    for template_config in GLOBAL_TEMPLATES:
        source_file = SOURCE_TEMPLATES_DIR / template_config["file_name"]

        if not source_file.exists():
            logger.warning(f"Template file not found: {source_file}")
            continue

        # Check if template with this name already exists (as global)
        existing = await db.execute(
            select(DocumentTemplate).where(
                DocumentTemplate.name == template_config["name"],
                DocumentTemplate.service_id.is_(None)
            )
        )
        if existing.scalar_one_or_none():
            logger.info(f"Global template already exists: {template_config['name']}")
            stats["templates_skipped"] += 1
            continue

        # Generate unique ID and copy file
        template_id = uuid_lib.uuid4()
        safe_filename = template_config["file_name"]
        dest_file = global_dir / f"{template_id}_{safe_filename}"

        # Copy file to templates directory
        shutil.copy2(source_file, dest_file)

        # Extract placeholders
        placeholders = document_template_service.extract_placeholders(dest_file)

        # Get file size
        file_size = dest_file.stat().st_size

        # Create database record (service_id=NULL for global)
        template = DocumentTemplate(
            id=template_id,
            name=template_config["name"],
            description=template_config["description"],
            service_id=None,  # Global template
            organization_id=None,
            file_path=str(dest_file.relative_to(document_template_service.TEMPLATES_DIR)),
            file_name=safe_filename,
            file_size=file_size,
            placeholders=placeholders,
            is_default=False,
        )

        db.add(template)
        logger.info(f"Created global template: {template_config['name']} ({template_id})")
        stats["templates_created"] += 1

    await db.flush()
    return stats
