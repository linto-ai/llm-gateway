#!/usr/bin/env python3
"""Pydantic schemas for FlavorPreset CRUD operations."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class FlavorPresetBase(BaseModel):
    """Base schema for FlavorPreset."""
    name: str = Field(..., min_length=1, max_length=100)
    service_type: str = Field(default="summary", max_length=50)
    description_en: Optional[str] = None
    description_fr: Optional[str] = None
    config: Dict[str, Any]


class FlavorPresetCreate(FlavorPresetBase):
    """Schema for creating a new flavor preset."""
    pass


class FlavorPresetUpdate(BaseModel):
    """Schema for updating a flavor preset."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description_en: Optional[str] = None
    description_fr: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class FlavorPresetResponse(FlavorPresetBase):
    """Schema for flavor preset response."""
    id: UUID
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
