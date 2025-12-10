#!/usr/bin/env python3
"""Seed global document templates from templates/default/ directory."""
import hashlib
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

# Global templates to seed (i18n format)
GLOBAL_TEMPLATES: List[Dict[str, Any]] = [
    {
        "file_name": "basic-report.docx",
        "name_fr": "Rapport de base",
        "name_en": "Basic Report",
        "description_fr": "Modele de rapport general avec titre, resume et sections de contenu. Adapte a tout type de service.",
        "description_en": "General-purpose report template with title, summary, and content sections. Suitable for any service type.",
    },
    {
        "file_name": "meeting-summary.docx",
        "name_fr": "Resume de reunion",
        "name_en": "Meeting Summary",
        "description_fr": "Modele de notes de reunion avec participants, date, ordre du jour et actions a entreprendre. Ideal pour les services de resume.",
        "description_en": "Meeting notes template with participants, date, agenda, and action items. Ideal for summarization services.",
    },
    {
        "file_name": "extraction-test.docx",
        "name_fr": "Rapport d'extraction",
        "name_en": "Extraction Report",
        "description_fr": "Modele pour les resultats d'extraction de metadonnees avec des espaces reserves dynamiques pour les champs extraits.",
        "description_en": "Template for metadata extraction results with dynamic placeholders for extracted fields.",
    },
    {
        "file_name": "silly-extraction-test.docx",
        "name_fr": "Test d'extraction fantaisiste",
        "name_en": "Silly Extraction Test",
        "description_fr": "Modele de test avec des espaces reserves fantaisistes pour les tests et demonstrations d'extraction.",
        "description_en": "Test template with whimsical placeholders for extraction testing and demonstration purposes.",
    },
]


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


async def seed_global_templates(db: AsyncSession) -> Dict[str, int]:
    """
    Seed global document templates from templates/default/ directory.

    Global templates have organization_id=NULL and user_id=NULL (system scope).

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

        # Check if template with this name already exists (as global/system scope)
        existing = await db.execute(
            select(DocumentTemplate).where(
                DocumentTemplate.name_fr == template_config["name_fr"],
                DocumentTemplate.organization_id.is_(None),
                DocumentTemplate.user_id.is_(None)
            )
        )
        if existing.scalar_one_or_none():
            logger.info(f"Global template already exists: {template_config['name_fr']}")
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

        # Get file size and hash
        file_size = dest_file.stat().st_size
        file_hash = calculate_file_hash(dest_file)

        # Create database record (system scope: org=NULL, user=NULL)
        template = DocumentTemplate(
            id=template_id,
            name_fr=template_config["name_fr"],
            name_en=template_config["name_en"],
            description_fr=template_config["description_fr"],
            description_en=template_config["description_en"],
            organization_id=None,  # System scope
            user_id=None,  # System scope
            file_path=str(dest_file.relative_to(document_template_service.TEMPLATES_DIR)),
            file_name=safe_filename,
            file_size=file_size,
            file_hash=file_hash,
            placeholders=placeholders,
            is_default=False,
        )

        db.add(template)
        logger.info(f"Created global template: {template_config['name_fr']} ({template_id})")
        stats["templates_created"] += 1

    await db.flush()
    return stats
