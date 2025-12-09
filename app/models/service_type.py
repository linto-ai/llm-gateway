#!/usr/bin/env python3
"""ServiceType model - Database-driven service type lookup table."""

import uuid
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ServiceType(Base):
    """Service type lookup table for dynamic service type management."""

    __tablename__ = "service_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(JSONB, nullable=False, default={})
    description = Column(JSONB, default={})
    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    display_order = Column(Integer, default=0)
    supports_reduce = Column(Boolean, default=False)
    supports_chunking = Column(Boolean, default=False)
    default_processing_mode = Column(String(20), default="single_pass")
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
    prompt_types = relationship("PromptType", back_populates="service_type", lazy="select")

    __table_args__ = (
        Index("idx_service_types_code", "code"),
        Index("idx_service_types_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<ServiceType(id={self.id}, code={self.code})>"
