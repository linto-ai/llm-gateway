#!/usr/bin/env python3
"""Association tables shared between models."""
from sqlalchemy import Column, ForeignKey, Table, Index
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

# Many-to-many link between services and the document templates available for them.
# When a service has no rows here, the available set falls back to the global
# default template (see document_template_service.get_default_template).
service_document_templates = Table(
    "service_document_templates",
    Base.metadata,
    Column(
        "service_id",
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "document_template_id",
        UUID(as_uuid=True),
        ForeignKey("document_templates.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Index("idx_service_document_templates_template", "document_template_id"),
)
