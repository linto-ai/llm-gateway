#!/usr/bin/env python3
import uuid
from sqlalchemy import Column, String, DateTime, Text, CheckConstraint, Index, UniqueConstraint, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Provider(Base):
    """Provider model for managing LLM API providers with encrypted credentials."""

    __tablename__ = "providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    provider_type = Column(String(50), nullable=False, index=True)
    api_base_url = Column(Text, nullable=False)
    api_key_encrypted = Column(Text, nullable=False)
    security_level = Column(Integer, nullable=False, default=1, index=True)
    provider_metadata = Column("metadata", JSONB, default={}, nullable=False, server_default='{}')
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
    models = relationship(
        "Model",
        back_populates="provider",
        cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("name", name="uq_provider_name"),
        CheckConstraint(
            "security_level IN (0, 1, 2)",
            name="check_security_level"
        ),
        Index("idx_providers_security", "security_level"),
        Index("idx_providers_type", "provider_type"),
    )

    def __repr__(self) -> str:
        return f"<Provider(id={self.id}, name={self.name}, type={self.provider_type})>"
