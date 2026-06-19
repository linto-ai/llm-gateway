#!/usr/bin/env python3
"""DocumentTemplate model for document generation templates."""
import uuid
from typing import Literal
from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
from app.core.database import Base


class DocumentTemplate(Base):
    """Document template for generating DOCX/PDF from job results.

    Visibility (multi-scope):
    - System templates: allowed_organization_ids=[], allowed_user_ids=[] (visible to all)
    - Organization templates: caller org in allowed_organization_ids
    - User templates: caller user in allowed_user_ids
    The legacy single organization_id/user_id columns are kept for backward
    compatibility (derived from the lists) and the `scope` string is derived
    from the lists.
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

    # Multi-scope access lists (free-form external IDs, no FK). Both empty =>
    # system template (visible to all). Mirror of the Service scoping model.
    allowed_organization_ids = Column(
        ARRAY(String(100)), nullable=False, server_default='{}'
    )
    allowed_user_ids = Column(
        ARRAY(String(100)), nullable=False, server_default='{}'
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
        Index(
            "idx_templates_allowed_orgs",
            "allowed_organization_ids",
            postgresql_using="gin",
        ),
        Index(
            "idx_templates_allowed_users",
            "allowed_user_ids",
            postgresql_using="gin",
        ),
    )

    @property
    def scope(self) -> Literal['system', 'organization', 'user']:
        """Return scope level derived from the access lists.

        - both lists empty -> system
        - any user listed   -> user
        - otherwise         -> organization
        """
        if not self.allowed_organization_ids and not self.allowed_user_ids:
            return "system"
        if self.allowed_user_ids:
            return "user"
        return "organization"

    def __repr__(self) -> str:
        return f"<DocumentTemplate(id={self.id}, name_fr={self.name_fr}, scope={self.scope})>"
