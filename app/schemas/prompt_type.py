#!/usr/bin/env python3
"""Schemas for prompt type CRUD operations."""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class PromptTypeBase(BaseModel):
    """Base schema for prompt types."""
    code: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-z][a-z0-9_]*$')
    name: dict = Field(..., description="i18n names {en, fr}")
    description: dict = Field(default_factory=dict)


class CreatePromptType(PromptTypeBase):
    """Schema for creating a new prompt type."""
    is_active: bool = True
    display_order: int = 0
    service_type_id: Optional[UUID] = Field(None, description="Optional link to a service type")


class UpdatePromptType(BaseModel):
    """Schema for updating a prompt type (partial update)."""
    name: Optional[dict] = None
    description: Optional[dict] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None
    service_type_id: Optional[UUID] = Field(None, description="Optional link to a service type")


class ServiceTypeNested(BaseModel):
    """Nested service type info for prompt type responses."""
    id: UUID
    code: str
    name: dict

    class Config:
        from_attributes = True


class PromptTypeResponse(BaseModel):
    """Schema for prompt type response."""
    id: UUID
    code: str
    name: dict
    description: dict
    is_system: bool
    is_active: bool
    display_order: int
    service_type_id: Optional[UUID] = None
    service_type: Optional[ServiceTypeNested] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
