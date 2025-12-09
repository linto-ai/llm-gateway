#!/usr/bin/env python3
"""FlavorUsage model for tracking flavor execution metrics and costs."""

import uuid
from sqlalchemy import Column, Integer, Float, Boolean, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class FlavorUsage(Base):
    """Usage tracking for service flavor executions."""

    __tablename__ = "flavor_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flavor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("service_flavors.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Usage metrics
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)
    latency_ms = Column(Integer, nullable=False)

    # Cost tracking
    estimated_cost = Column(Float, nullable=True)

    # Status
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    executed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # Relationships
    flavor = relationship("ServiceFlavor", back_populates="usage_records")
    job = relationship("Job", back_populates="flavor_usages")

    __table_args__ = (
        Index('idx_flavor_usage_flavor', 'flavor_id'),
        Index('idx_flavor_usage_job', 'job_id'),
        Index('idx_flavor_usage_executed_at', 'executed_at'),
        Index('idx_flavor_usage_success', 'success'),
    )

    def __repr__(self) -> str:
        return f"<FlavorUsage(id={self.id}, flavor_id={self.flavor_id}, tokens={self.total_tokens})>"
