#!/usr/bin/env python3
import uuid
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Boolean, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import TYPE_CHECKING
from app.core.database import Base
from app.models.associations import service_document_templates

if TYPE_CHECKING:
    pass


class Service(Base):
    """Service definitions for LLM-powered text processing workflows."""

    __tablename__ = "services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    route = Column(String(100), nullable=False, index=True)
    service_type = Column(String(50), nullable=False, index=True)
    description = Column(JSONB, nullable=False, default={}, server_default='{}')
    # Legacy single-org identifier (no FK constraint). Kept for backward compat:
    # populated/derived from allowed_organization_ids, still returned to clients
    # that read a single organization_id (e.g. LinTO Studio).
    organization_id = Column(String(100), nullable=True, index=True)
    # Multi-scope access lists (free-form external IDs, no FK). A service is
    # visible if the caller's org is in allowed_organization_ids OR the caller's
    # user is in allowed_user_ids OR both lists are empty (= global service).
    allowed_organization_ids = Column(
        ARRAY(String(100)), nullable=False, server_default='{}'
    )
    allowed_user_ids = Column(
        ARRAY(String(100)), nullable=False, server_default='{}'
    )
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    service_metadata = Column("metadata", JSONB, default={}, nullable=False, server_default='{}')
    
    # Allows custom service types
    service_category = Column(String(50), nullable=True, default='custom')

    # Default template for document generation output
    default_template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_templates.id", ondelete="SET NULL"),
        nullable=True
    )

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

    # Relationships
    flavors = relationship(
        "ServiceFlavor",
        back_populates="service",
        cascade="all, delete-orphan"
    )
    jobs = relationship("Job", back_populates="service", passive_deletes=True)
    # Document templates explicitly made available for this service. Empty set =>
    # fall back to the global default template (see get_service_templates).
    document_templates = relationship(
        "DocumentTemplate",
        secondary=service_document_templates,
        lazy="selectin",
    )

    # Constraints (service_type validation moved to lookup table)
    # Note: per-org unique constraints on (name) / (route) were dropped when
    # services gained multi-org/user scoping (no single scalar scope to key on).
    # Studio resolves services by first name/route match, so admins keep these
    # unique; plain indexes below speed lookups.
    __table_args__ = (
        Index("idx_services_org", "organization_id"),
        Index("idx_services_type", "service_type"),
        Index("idx_services_active", "is_active"),
        Index("idx_services_route", "route"),
        Index("idx_services_name", "name"),
        Index(
            "idx_services_allowed_orgs",
            "allowed_organization_ids",
            postgresql_using="gin",
        ),
        Index(
            "idx_services_allowed_users",
            "allowed_user_ids",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        return f"<Service(id={self.id}, name={self.name}, route={self.route})>"
