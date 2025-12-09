#!/usr/bin/env python3
"""Document template service for DOCX template management."""
import logging
import re
import os
import uuid as uuid_lib
from pathlib import Path
from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import UploadFile

from app.models.document_template import DocumentTemplate
from app.models.service import Service

logger = logging.getLogger(__name__)


class DocumentTemplateService:
    """Service for managing document templates for DOCX/PDF export."""

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    ALLOWED_MIME_TYPES = [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    DOCX_MAGIC_BYTES = b"PK"  # DOCX is a ZIP file

    def __init__(self):
        """Initialize template service."""
        # Use env var for templates dir, default to /var/www/data/templates
        self.TEMPLATES_DIR = Path(os.environ.get("TEMPLATES_DIR", "/var/www/data/templates"))
        # Ensure templates directory exists
        self.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

    async def create_template(
        self,
        db: AsyncSession,
        service_id: UUID,
        file: UploadFile,
        name: str,
        description: Optional[str] = None,
        is_default: bool = False,
        organization_id: Optional[UUID] = None,
    ) -> DocumentTemplate:
        """
        Upload and register a new DOCX template.

        Args:
            db: Database session
            service_id: Service to associate template with
            file: Uploaded file
            name: Template name
            description: Optional description
            is_default: Whether to set as default for service
            organization_id: Optional organization scope

        Returns:
            Created DocumentTemplate

        Raises:
            ValueError: If file is invalid
        """
        # Validate file
        content = await file.read()
        await file.seek(0)

        if len(content) > self.MAX_FILE_SIZE:
            raise ValueError(f"File exceeds maximum size of {self.MAX_FILE_SIZE // (1024*1024)}MB")

        if not content.startswith(self.DOCX_MAGIC_BYTES):
            raise ValueError("Invalid file format. Only DOCX files are accepted.")

        # Generate unique file path
        template_id = uuid_lib.uuid4()
        service_dir = self.TEMPLATES_DIR / f"service_{service_id}"
        service_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_filename = self._sanitize_filename(file.filename or "template.docx")
        file_path = service_dir / f"{template_id}_{safe_filename}"

        # Save file to disk
        with open(file_path, "wb") as f:
            f.write(content)

        # Extract placeholders from the document
        placeholders = self.extract_placeholders(file_path)

        # If setting as default, unset any existing default for this service
        if is_default:
            await self._clear_default_for_service(db, service_id)

        # Create database record
        template = DocumentTemplate(
            id=template_id,
            name=name,
            description=description,
            service_id=service_id,
            organization_id=organization_id,
            file_path=str(file_path.relative_to(self.TEMPLATES_DIR)),
            file_name=safe_filename,
            file_size=len(content),
            placeholders=placeholders,
            is_default=is_default,
        )

        db.add(template)
        await db.flush()
        await db.refresh(template)

        # Update service default_template_id if this is the default
        if is_default:
            await db.execute(
                update(Service)
                .where(Service.id == service_id)
                .values(default_template_id=template.id)
            )

        logger.info(f"Created template: {name} ({template.id}) for service {service_id}")
        return template

    async def get_template(
        self,
        db: AsyncSession,
        template_id: UUID
    ) -> Optional[DocumentTemplate]:
        """Get template by ID."""
        result = await db.execute(
            select(DocumentTemplate).where(DocumentTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def list_templates(
        self,
        db: AsyncSession,
        service_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        include_global: bool = False,
        global_only: bool = False,
    ) -> List[DocumentTemplate]:
        """
        List templates, optionally filtered by service or organization.

        Args:
            db: Database session
            service_id: Optional service filter
            organization_id: Optional organization filter
            include_global: Also include global templates (service_id=NULL)
            global_only: Only return global templates (service_id=NULL)

        Returns:
            List of DocumentTemplate objects
        """
        from sqlalchemy import or_

        query = select(DocumentTemplate)

        if global_only:
            # Only global templates
            query = query.where(DocumentTemplate.service_id.is_(None))
        elif service_id:
            if include_global:
                # Service templates + global templates
                query = query.where(
                    or_(
                        DocumentTemplate.service_id == service_id,
                        DocumentTemplate.service_id.is_(None)
                    )
                )
            else:
                query = query.where(DocumentTemplate.service_id == service_id)

        if organization_id:
            query = query.where(DocumentTemplate.organization_id == organization_id)

        query = query.order_by(DocumentTemplate.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def delete_template(
        self,
        db: AsyncSession,
        template_id: UUID
    ) -> bool:
        """
        Delete template (file + DB record).

        Args:
            db: Database session
            template_id: Template to delete

        Returns:
            True if deleted, False if not found
        """
        template = await self.get_template(db, template_id)
        if not template:
            return False

        # Delete file from disk
        file_path = self.TEMPLATES_DIR / template.file_path
        if file_path.exists():
            file_path.unlink()

        # If this was the default, clear the service reference
        if template.is_default and template.service_id:
            await db.execute(
                update(Service)
                .where(Service.id == template.service_id)
                .values(default_template_id=None)
            )

        # Delete database record
        await db.delete(template)

        logger.info(f"Deleted template: {template.name} ({template_id})")
        return True

    async def set_default_template(
        self,
        db: AsyncSession,
        service_id: UUID,
        template_id: UUID
    ) -> bool:
        """
        Set template as default for a service.

        Args:
            db: Database session
            service_id: Service ID
            template_id: Template to set as default

        Returns:
            True if successful, False if template not found
        """
        template = await self.get_template(db, template_id)
        if not template or template.service_id != service_id:
            return False

        # Clear existing default
        await self._clear_default_for_service(db, service_id)

        # Set new default
        template.is_default = True
        await db.execute(
            update(Service)
            .where(Service.id == service_id)
            .values(default_template_id=template_id)
        )

        logger.info(f"Set default template for service {service_id}: {template.name}")
        return True

    async def get_default_template(
        self,
        db: AsyncSession,
        service_id: UUID
    ) -> Optional[DocumentTemplate]:
        """Get the default template for a service."""
        result = await db.execute(
            select(DocumentTemplate).where(
                DocumentTemplate.service_id == service_id,
                DocumentTemplate.is_default
            )
        )
        return result.scalar_one_or_none()

    def extract_placeholders(self, file_path: Path) -> List[str]:
        """
        Parse DOCX and extract {{placeholder}} patterns.

        Args:
            file_path: Path to DOCX file

        Returns:
            List of placeholder names (without braces)
        """
        try:
            from docx import Document
        except ImportError:
            logger.warning("python-docx not installed, cannot extract placeholders")
            return []

        placeholders = set()
        pattern = r'\{\{([^}]+)\}\}'

        try:
            doc = Document(file_path)

            # Search paragraphs
            for para in doc.paragraphs:
                placeholders.update(re.findall(pattern, para.text))

            # Search tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        placeholders.update(re.findall(pattern, cell.text))

            # Search headers/footers
            for section in doc.sections:
                if section.header:
                    for para in section.header.paragraphs:
                        placeholders.update(re.findall(pattern, para.text))
                if section.footer:
                    for para in section.footer.paragraphs:
                        placeholders.update(re.findall(pattern, para.text))

        except Exception as e:
            logger.warning(f"Error extracting placeholders from {file_path}: {e}")

        return sorted(list(placeholders))

    def get_file_path(self, template: DocumentTemplate) -> Path:
        """Get absolute file path for a template."""
        return self.TEMPLATES_DIR / template.file_path

    async def _clear_default_for_service(
        self,
        db: AsyncSession,
        service_id: UUID
    ) -> None:
        """Clear is_default flag for all templates of a service."""
        await db.execute(
            update(DocumentTemplate)
            .where(
                DocumentTemplate.service_id == service_id,
                DocumentTemplate.is_default
            )
            .values(is_default=False)
        )

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal."""
        # Remove any path components
        filename = os.path.basename(filename)
        # Remove potentially dangerous characters
        filename = re.sub(r'[^\w\.\-]', '_', filename)
        # Ensure it ends with .docx
        if not filename.lower().endswith('.docx'):
            filename += '.docx'
        return filename

    async def import_template(
        self,
        db: AsyncSession,
        template_id: UUID,
        service_id: UUID,
        new_name: Optional[str] = None,
        organization_id: Optional[UUID] = None,
    ) -> DocumentTemplate:
        """
        Import a global template to a service (copy).

        Args:
            db: Database session
            template_id: Source template ID (must be global)
            service_id: Target service ID
            new_name: Optional new name (defaults to original name)
            organization_id: Optional organization scope

        Returns:
            New DocumentTemplate copy

        Raises:
            ValueError: If source template not found or not global
        """
        import shutil

        # Get source template
        source = await self.get_template(db, template_id)
        if not source:
            raise ValueError("Source template not found")

        if source.service_id is not None:
            raise ValueError("Can only import global templates (service_id must be NULL)")

        # Get source file path
        source_path = self.get_file_path(source)
        if not source_path.exists():
            raise ValueError("Source template file not found on disk")

        # Generate new template ID and destination path
        new_id = uuid_lib.uuid4()
        service_dir = self.TEMPLATES_DIR / f"service_{service_id}"
        service_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = self._sanitize_filename(source.file_name)
        dest_path = service_dir / f"{new_id}_{safe_filename}"

        # Copy file
        shutil.copy2(source_path, dest_path)

        # Get file size
        file_size = dest_path.stat().st_size

        # Create new template record
        new_template = DocumentTemplate(
            id=new_id,
            name=new_name or source.name,
            description=source.description,
            service_id=service_id,
            organization_id=organization_id,
            file_path=str(dest_path.relative_to(self.TEMPLATES_DIR)),
            file_name=safe_filename,
            file_size=file_size,
            placeholders=source.placeholders,
            is_default=False,
        )

        db.add(new_template)
        await db.flush()
        await db.refresh(new_template)

        logger.info(f"Imported template '{source.name}' ({template_id}) to service {service_id} as '{new_template.name}' ({new_id})")
        return new_template


# Singleton instance
document_template_service = DocumentTemplateService()
