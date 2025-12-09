#!/usr/bin/env python3
"""DocumentTemplate model for document generation templates."""
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class DocumentTemplate(Base):
    """Document template for generating DOCX/PDF from job results."""

    __tablename__ = "document_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    service_id = Column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    # Free-form organization identifier (no FK constraint)
    organization_id = Column(String(100), nullable=True, index=True)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(
        String(100),
        default='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        nullable=False
    )
    placeholders = Column(JSONB, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
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
    service = relationship(
        "Service",
        back_populates="templates",
        foreign_keys=[service_id]
    )

    __table_args__ = (
        Index("idx_templates_service_id", "service_id"),
        Index("idx_templates_org_id", "organization_id"),
    )

    def __repr__(self) -> str:
        return f"<DocumentTemplate(id={self.id}, name={self.name}, service_id={self.service_id})>"
