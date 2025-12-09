#!/usr/bin/env python3
"""Schemas for service type CRUD operations and configuration responses."""

from typing import Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


# ============================================================================
# Database-driven service type schemas (CRUD)
# ============================================================================

class ServiceTypeBase(BaseModel):
    """Base schema for service types."""
    code: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-z][a-z0-9_]*$')
    name: dict = Field(..., description="i18n names {en, fr}")
    description: dict = Field(default_factory=dict)


class CreateServiceType(ServiceTypeBase):
    """Schema for creating a new service type."""
    is_active: bool = True
    display_order: int = 0


class UpdateServiceType(BaseModel):
    """Schema for updating a service type (partial update)."""
    name: Optional[dict] = None
    description: Optional[dict] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class ServiceTypeResponse(BaseModel):
    """Schema for service type response (database-driven)."""
    id: UUID
    code: str
    name: dict
    description: dict
    is_system: bool
    is_active: bool
    display_order: int
    supports_reduce: bool = False
    supports_chunking: bool = False
    default_processing_mode: str = "single_pass"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Configuration-based service type schemas (existing pattern for prompt fields)
# ============================================================================

class PromptFieldConfigResponse(BaseModel):
    """Response schema for prompt field configuration."""
    required: bool
    prompt_category: str  # 'system' or 'user'
    prompt_type: Optional[str] = None  # 'standard', 'reduce', or custom
    description_en: str
    description_fr: str


class ServiceTypeConfigResponse(BaseModel):
    """Response schema for service type configuration (from SERVICE_TYPE_CONFIGS)."""
    type: str
    name_en: str
    name_fr: str
    description_en: str
    description_fr: str
    prompts: Dict[str, PromptFieldConfigResponse]
    supports_reduce: bool
    supports_chunking: bool
    default_processing_mode: str
