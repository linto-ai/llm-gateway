#!/usr/bin/env python3
import uuid
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Float, Integer, Boolean, Text,
    CheckConstraint, Index, UniqueConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ServiceFlavor(Base):
    """Model-specific configurations for services (formerly 'flavors' in Hydra config)."""

    __tablename__ = "service_flavors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id = Column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    model_id = Column(
        UUID(as_uuid=True),
        ForeignKey("models.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    name = Column(String(50), nullable=False)
    temperature = Column(Float, nullable=False)
    top_p = Column(Float, nullable=False)
    
    # Default flavor flag
    is_default = Column(Boolean, nullable=False, default=False)

    # Advanced configuration
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    frequency_penalty = Column(Float, nullable=False, default=0.0)
    presence_penalty = Column(Float, nullable=False, default=0.0)
    stop_sequences = Column(JSONB, nullable=False, default=list, server_default='[]')
    custom_params = Column(JSONB, nullable=False, default=dict, server_default='{}')
    estimated_cost_per_1k_tokens = Column(Float, nullable=True)
    max_concurrent_requests = Column(Integer, nullable=True)
    priority = Column(Integer, nullable=False, default=5, index=True)

    # Chunking/Resampling parameters - control how long text input is processed
    # These parameters define how the chunker splits and batches content for iterative processing
    create_new_turn_after = Column(Integer, nullable=True)  # Token threshold for creating new turn
    summary_turns = Column(Integer, nullable=True)          # Summary turns kept in context
    max_new_turns = Column(Integer, nullable=True)          # Max turns per summarization batch
    reduce_summary = Column(Boolean, default=False, nullable=False)
    consolidate_summary = Column(Boolean, default=False, nullable=False)

    output_type = Column(String(50), nullable=False)

    # Prompt references (template IDs - for tracking origin)
    system_prompt_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="SET NULL"),
        nullable=True
    )
    user_prompt_template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="SET NULL"),
        nullable=True
    )
    reduce_prompt_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Inline prompt content (actual content used)
    prompt_system_content = Column(Text, nullable=True)
    prompt_user_content = Column(Text, nullable=True)
    prompt_reduce_content = Column(Text, nullable=True)
    

    # Tokenizer override
    tokenizer_override = Column(String(200), nullable=True)

    # Processing mode configuration
    processing_mode = Column(
        String(20),
        nullable=False,
        default="iterative",
        server_default="iterative",
        comment="Processing strategy: 'single_pass' or 'iterative'"
    )

    # Fallback configuration - explicit flavor to use when context is exceeded
    fallback_flavor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("service_flavors.id", ondelete="SET NULL"),
        nullable=True,
        comment="Specific flavor to fallback to when input exceeds context limit"
    )

    # Failover configuration - triggers on processing errors (different from context fallback)
    failover_flavor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("service_flavors.id", ondelete="SET NULL"),
        nullable=True,
        comment="Flavor to use when this flavor fails during processing"
    )
    failover_enabled = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Enable automatic failover on processing errors"
    )
    failover_on_timeout = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Failover when API timeout occurs"
    )
    failover_on_rate_limit = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Failover when rate limit is exceeded (after retries)"
    )
    failover_on_model_error = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Failover when model returns error (503, 404, etc.)"
    )
    failover_on_content_filter = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Failover when content filter is triggered"
    )
    max_failover_depth = Column(
        Integer,
        nullable=False,
        default=3,
        server_default="3",
        comment="Maximum depth of failover chain (prevents infinite loops)"
    )

    # Placeholder extraction configuration
    placeholder_extraction_prompt_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="SET NULL"),
        nullable=True
    )

    # Categorization prompt configuration
    categorization_prompt_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="SET NULL"),
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
    service = relationship("Service", back_populates="flavors")
    model = relationship("Model", back_populates="service_flavors")
    system_prompt = relationship("Prompt", foreign_keys=[system_prompt_id])
    user_prompt_template = relationship("Prompt", foreign_keys=[user_prompt_template_id])
    jobs = relationship("Job", back_populates="flavor", passive_deletes=True)
    reduce_prompt = relationship("Prompt", foreign_keys=[reduce_prompt_id])
    placeholder_extraction_prompt = relationship("Prompt", foreign_keys=[placeholder_extraction_prompt_id])
    categorization_prompt = relationship("Prompt", foreign_keys=[categorization_prompt_id])
    usage_records = relationship("FlavorUsage", back_populates="flavor", cascade="all, delete-orphan")
    fallback_flavor = relationship("ServiceFlavor", remote_side=[id], foreign_keys=[fallback_flavor_id])
    failover_flavor = relationship("ServiceFlavor", remote_side=[id], foreign_keys=[failover_flavor_id])

    # Constraints
    __table_args__ = (
        UniqueConstraint("service_id", "name", name="uq_service_flavor_name"),
        CheckConstraint(
            "temperature >= 0 AND temperature <= 2",
            name="check_temperature"
        ),
        CheckConstraint(
            "top_p > 0 AND top_p <= 1",
            name="check_top_p"
        ),
        CheckConstraint(
            "output_type IN ('text', 'markdown', 'json')",
            name="check_output_type"
        ),
        CheckConstraint(
            "frequency_penalty >= 0 AND frequency_penalty <= 2",
            name="check_frequency_penalty"
        ),
        CheckConstraint(
            "presence_penalty >= 0 AND presence_penalty <= 2",
            name="check_presence_penalty"
        ),
        CheckConstraint(
            "priority >= 0 AND priority <= 9",
            name="check_priority"
        ),
        CheckConstraint(
            "processing_mode IN ('single_pass', 'iterative')",
            name="check_processing_mode"
        ),
        # Failover chain constraints
        CheckConstraint(
            "failover_flavor_id IS NULL OR failover_flavor_id != id",
            name="check_no_self_failover"
        ),
        CheckConstraint(
            "max_failover_depth >= 1 AND max_failover_depth <= 10",
            name="check_max_failover_depth"
        ),
        # Unique partial index for is_default (only one default per service)
        Index("idx_service_flavors_default", "service_id", unique=True,
              postgresql_where=text("is_default = true")),
        Index("idx_flavors_service", "service_id"),
        Index("idx_flavors_model", "model_id"),
        Index("idx_flavors_system_prompt", "system_prompt_id"),
        Index("idx_flavors_user_prompt", "user_prompt_template_id"),
        Index("idx_flavors_reduce_prompt", "reduce_prompt_id"),
        Index("idx_flavors_placeholder_prompt", "placeholder_extraction_prompt_id"),
        Index("idx_flavors_categorization_prompt", "categorization_prompt_id"),
        Index("idx_flavors_fallback", "fallback_flavor_id"),
        Index("idx_flavors_failover", "failover_flavor_id"),
        Index("idx_flavors_active", "is_active"),
        Index("idx_flavors_priority", "priority", postgresql_ops={'priority': 'DESC'}),
    )

    def __repr__(self) -> str:
        return f"<ServiceFlavor(id={self.id}, name={self.name}, service_id={self.service_id})>"
