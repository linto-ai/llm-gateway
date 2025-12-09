#!/usr/bin/env python3
import uuid
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Boolean, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import TYPE_CHECKING
from app.core.database import Base

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
    # Free-form organization identifier (no FK constraint)
    organization_id = Column(String(100), nullable=True, index=True)
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
    templates = relationship(
        "DocumentTemplate",
        back_populates="service",
        cascade="all, delete-orphan",
        foreign_keys="DocumentTemplate.service_id"
    )

    # Constraints (service_type validation moved to lookup table)
    __table_args__ = (
        UniqueConstraint("name", "organization_id", name="uq_service_name_org"),
        UniqueConstraint("route", "organization_id", name="uq_service_route_org"),
        Index("idx_services_org", "organization_id"),
        Index("idx_services_type", "service_type"),
        Index("idx_services_active", "is_active"),
        Index("idx_services_route", "route"),
    )

    def __repr__(self) -> str:
        return f"<Service(id={self.id}, name={self.name}, route={self.route})>"
