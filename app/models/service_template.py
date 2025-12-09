#!/usr/bin/env python3
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class ServiceTemplate(Base):
    """Pre-configured service blueprints."""

    __tablename__ = "service_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    service_type = Column(String(50), nullable=False)
    description = Column(JSONB, nullable=False, default={})
    is_public = Column(Boolean, nullable=False, default=True)
    default_config = Column(JSONB, nullable=False)
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
        CheckConstraint(
            "service_type IN ('summary', 'translation', 'categorization', 'diarization_correction', 'speaker_correction', 'generic')",
            name="check_template_service_type"
        ),
        Index("idx_templates_type", "service_type"),
        Index("idx_templates_public", "is_public"),
    )

    def __repr__(self) -> str:
        return f"<ServiceTemplate(id={self.id}, name={self.name}, type={self.service_type})>"
