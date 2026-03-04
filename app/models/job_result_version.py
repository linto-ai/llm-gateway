"""JobResultVersion model for storing version history of job results."""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class JobResultVersion(Base):
    """Version history for job results.

    Stores full content for each version.
    """

    __tablename__ = "job_result_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    diff = Column(Text, nullable=False)  # Unused, kept for DB compatibility
    full_content = Column(Text, nullable=True)  # Full version content
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String(255), nullable=True)

    # Relationship back to Job
    job = relationship("Job", back_populates="versions")

    __table_args__ = (
        UniqueConstraint('job_id', 'version_number', name='unique_job_version'),
    )

    def __repr__(self) -> str:
        return f"<JobResultVersion(job_id={self.job_id}, version={self.version_number})>"
