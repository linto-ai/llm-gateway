"""Job model for tracking task execution."""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
import uuid

from app.core.database import Base


class Job(Base):
    """Job execution tracking model."""

    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    flavor_id = Column(UUID(as_uuid=True), ForeignKey("service_flavors.id", ondelete="SET NULL"), nullable=True)
    # Free-form organization identifier (no FK constraint)
    organization_id = Column(String(100), nullable=True, index=True)

    status = Column(String(20), nullable=False, default="queued")
    celery_task_id = Column(String(255), unique=True, nullable=False)

    input_file_name = Column(String(255), nullable=True)
    input_content_preview = Column(Text, nullable=True)
    result = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    progress = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Version tracking for inline editing
    current_version = Column(Integer, nullable=False, default=1)
    last_edited_at = Column(DateTime(timezone=True), nullable=True)

    # Fallback tracking (when input exceeds context limit)
    fallback_applied = Column(String(5), nullable=False, default="false")  # 'true' or 'false'
    original_flavor_id = Column(UUID(as_uuid=True), nullable=True)
    original_flavor_name = Column(String(50), nullable=True)
    fallback_reason = Column(Text, nullable=True)
    fallback_input_tokens = Column(Integer, nullable=True)
    fallback_context_available = Column(Integer, nullable=True)

    # TTL / Expiration
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this job expires and can be cleaned up. NULL = never."
    )

    # Relationships
    service = relationship("Service", back_populates="jobs")
    flavor = relationship("ServiceFlavor", back_populates="jobs")
    flavor_usages = relationship("FlavorUsage", back_populates="job")
    versions = relationship("JobResultVersion", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'started', 'processing', 'completed', 'failed')",
            name="valid_status"
        ),
    )
