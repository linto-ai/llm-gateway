#!/usr/bin/env python3
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class ServiceTemplateResponse(BaseModel):
    """Schema for service template response."""
    id: UUID
    name: str
    service_type: str
    description: dict
    is_public: bool
    default_config: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ServiceTemplateListResponse(BaseModel):
    """Schema for template list."""
    items: list[ServiceTemplateResponse]


class CreateFromTemplate(BaseModel):
    """Schema for creating a service from a template."""
    name: str = Field(..., min_length=1, max_length=100)
    route: str = Field(..., min_length=1, max_length=100)
    organization_id: Optional[UUID] = None
    model_id: UUID
    customizations: Optional[dict] = None


class CreateFromTemplateResponse(BaseModel):
    """Schema for response when creating from template."""
    service: dict
    flavor: dict
