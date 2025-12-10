#!/usr/bin/env python3
"""DocumentTemplate model for document generation templates."""
import uuid
from typing import Literal
from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class DocumentTemplate(Base):
    """Document template for generating DOCX/PDF from job results.

    Visibility hierarchy:
    - System templates: organization_id=NULL, user_id=NULL (visible to all)
    - Organization templates: organization_id=X, user_id=NULL (visible to org X)
    - User templates: organization_id=X, user_id=Y (visible only to user Y)
    """

    __tablename__ = "document_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # i18n name fields
    name_fr = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=True)

    # i18n description fields
    description_fr = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)

    # Hierarchical scoping
    # Using String instead of UUID for flexibility with external systems
    # (e.g., MongoDB ObjectIds, custom IDs, etc.)
    organization_id = Column(
        String(100),
        nullable=True,
        index=True
    )
    user_id = Column(
        String(100),
        nullable=True,
        index=True
    )

    # File information
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_hash = Column(String(64), nullable=True)  # SHA256 hash
    mime_type = Column(
        String(100),
        default='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        nullable=False
    )

    # Parsed placeholders from template
    placeholders = Column(JSONB, nullable=True)

    # Default flag (for system-level default marking)
    is_default = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    __table_args__ = (
        Index("idx_templates_org_id", "organization_id"),
        Index("idx_templates_user_id", "user_id"),
        Index("idx_templates_scope", "organization_id", "user_id"),
        Index("idx_templates_file_hash", "file_hash"),
        # Constraint: user_id requires organization_id
        CheckConstraint(
            "(user_id IS NULL) OR (organization_id IS NOT NULL)",
            name="check_user_requires_org"
        ),
    )

    @property
    def scope(self) -> Literal['system', 'organization', 'user']:
        """Return scope level: system, organization, or user."""
        if self.organization_id is None and self.user_id is None:
            return "system"
        elif self.user_id is None:
            return "organization"
        return "user"

    def __repr__(self) -> str:
        return f"<DocumentTemplate(id={self.id}, name_fr={self.name_fr}, scope={self.scope})>"
