#!/usr/bin/env python3
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Prompt(Base):
    """Prompt storage (replaces file-based prompts)."""

    __tablename__ = "prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    description = Column(JSONB, nullable=False, default={})
    # Free-form organization identifier (no FK constraint)
    organization_id = Column(String(100), nullable=True, index=True)

    # Category: how the prompt is used in LLM call (required)
    # Values: 'system' or 'user'
    prompt_category = Column(
        String(50),
        nullable=False,
        index=True,
        comment="How prompt is used: 'system' or 'user'"
    )

    # Prompt type: what the prompt does (optional, FK to prompt_types)
    # Replaces the old prompt_role column with proper FK
    prompt_type_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prompt_types.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    parent_template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Service type affinity (required field)
    service_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Service type affinity: summary, translation, categorization, etc."
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
    parent_template = relationship("Prompt", remote_side=[id], backref="derived_templates")
    prompt_type = relationship("PromptType")

    # Constraints
    __table_args__ = (
        UniqueConstraint("name", "organization_id", name="uq_prompt_name_org"),
        CheckConstraint(
            "prompt_category IN ('system', 'user')",
            name="check_prompt_category"
        ),
        Index("idx_prompts_org", "organization_id"),
        Index("idx_prompts_name", "name"),
        Index("idx_prompts_prompt_category", "prompt_category"),
        Index("idx_prompts_prompt_type", "prompt_type_id"),
        Index("idx_prompts_parent_template", "parent_template_id"),
        Index("idx_prompts_service_type", "service_type"),
    )

    def __repr__(self) -> str:
        return f"<Prompt(id={self.id}, name={self.name})>"
