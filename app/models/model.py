#!/usr/bin/env python3
import uuid
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Integer, Boolean, Text,
    CheckConstraint, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Model(Base):
    """Model catalog for LLM models with technical specifications."""

    __tablename__ = "models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(
        UUID(as_uuid=True),
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    model_name = Column(String(200), nullable=False)
    model_identifier = Column(String(200), nullable=False)
    context_length = Column(Integer, nullable=False)
    max_generation_length = Column(Integer, nullable=False)
    tokenizer_class = Column(String(100), nullable=True)
    tokenizer_name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Health monitoring fields (replaces is_verified)
    health_status = Column(
        String(20),
        nullable=False,
        default='unknown',
        index=True
    )
    health_checked_at = Column(DateTime(timezone=True), nullable=True)
    health_error = Column(Text, nullable=True)
    
    model_metadata = Column("metadata", JSONB, default={}, nullable=False, server_default='{}')

    # Extended fields
    huggingface_repo = Column(String(500), nullable=True)
    security_level = Column(String(50), nullable=True)
    deployment_name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    best_use = Column(Text, nullable=True)
    usage_type = Column(String(50), nullable=True)
    system_prompt = Column(Text, nullable=True)

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
    provider = relationship("Provider", back_populates="models")
    service_flavors = relationship(
        "ServiceFlavor",
        back_populates="model",
        cascade="all, delete-orphan"
    )

    # Computed properties for Pydantic serialization
    @property
    def provider_name(self) -> str:
        """Get provider name from relationship (for Pydantic serialization)."""
        return self.provider.name if self.provider else None

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "provider_id", "model_identifier",
            name="uq_provider_model_identifier"
        ),
        CheckConstraint("context_length > 0", name="check_context_length"),
        CheckConstraint("max_generation_length > 0", name="check_max_gen_length"),
        CheckConstraint(
            "health_status IN ('available', 'unavailable', 'unknown', 'error')",
            name="check_health_status"
        ),
        Index("idx_models_provider", "provider_id"),
        Index("idx_models_active", "is_active"),
        Index("idx_models_health_status", "health_status"),
    )

    def __repr__(self) -> str:
        return f"<Model(id={self.id}, name={self.model_name}, identifier={self.model_identifier})>"
