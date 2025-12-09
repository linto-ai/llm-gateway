#!/usr/bin/env python3
"""FlavorPreset ORM model for pre-configured flavor settings."""

import uuid
from sqlalchemy import Column, String, Boolean, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class FlavorPreset(Base):
    """Pre-configured flavor settings that can be applied to create new flavors."""

    __tablename__ = "flavor_presets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    service_type = Column(String(50), nullable=False, default="summary", index=True)
    description_en = Column(Text, nullable=True)
    description_fr = Column(Text, nullable=True)
    is_system = Column(Boolean, nullable=False, default=False, server_default="false")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    config = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_flavor_presets_service_type", "service_type"),
    )

    def __repr__(self) -> str:
        return f"<FlavorPreset(id={self.id}, name={self.name}, service_type={self.service_type})>"
