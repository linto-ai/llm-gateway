#!/usr/bin/env python3
"""PromptType model - Database-driven prompt type lookup table."""

import uuid
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class PromptType(Base):
    """Prompt type lookup table for dynamic prompt type management."""

    __tablename__ = "prompt_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(JSONB, nullable=False, default={})
    description = Column(JSONB, default={})
    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    display_order = Column(Integer, default=0)
    service_type_id = Column(
        UUID(as_uuid=True),
        ForeignKey("service_types.id", ondelete="SET NULL"),
        nullable=True,
        index=True
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
    service_type = relationship("ServiceType", back_populates="prompt_types", lazy="joined")

    __table_args__ = (
        Index("idx_prompt_types_code", "code"),
        Index("idx_prompt_types_active", "is_active"),
        Index("idx_prompt_types_service_type", "service_type_id"),
    )

    def __repr__(self) -> str:
        return f"<PromptType(id={self.id}, code={self.code})>"
