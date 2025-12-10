#!/usr/bin/env python3
"""Pydantic schemas for document templates."""
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID


class TemplateCreate(BaseModel):
    """Schema for creating a new document template (via multipart form)."""
    name_fr: str = Field(..., min_length=1, max_length=255)
    name_en: Optional[str] = Field(None, max_length=255)
    description_fr: Optional[str] = None
    description_en: Optional[str] = None
    # Using str instead of UUID for flexibility with external systems
    organization_id: Optional[str] = Field(None, max_length=100)
    user_id: Optional[str] = Field(None, max_length=100)
    is_default: bool = False

    @model_validator(mode='after')
    def validate_user_requires_org(self):
        """Validate that user_id requires organization_id."""
        if self.user_id is not None and self.organization_id is None:
            raise ValueError("user_id requires organization_id to be set")
        return self


class TemplateUpdate(BaseModel):
    """Schema for updating a document template."""
    name_fr: Optional[str] = Field(None, min_length=1, max_length=255)
    name_en: Optional[str] = Field(None, max_length=255)
    description_fr: Optional[str] = None
    description_en: Optional[str] = None
    is_default: Optional[bool] = None


class TemplateResponse(BaseModel):
    """Schema for document template response."""
    id: UUID
    name_fr: str
    name_en: Optional[str]
    description_fr: Optional[str]
    description_en: Optional[str]
    # Using str instead of UUID for flexibility with external systems
    organization_id: Optional[str]
    user_id: Optional[str]
    file_path: str
    file_name: str
    file_size: int
    file_hash: Optional[str]
    mime_type: str
    placeholders: Optional[List[str]]
    is_default: bool
    scope: Literal['system', 'organization', 'user']
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Response schema for listing templates."""
    items: List[TemplateResponse]
    total: int


class PlaceholderInfo(BaseModel):
    """Information about a single placeholder."""
    name: str
    description: Optional[str] = None
    is_standard: bool = False


class AllPlaceholdersResponse(BaseModel):
    """Response with all available placeholders for document generation."""
    standard: List[PlaceholderInfo]
    template: List[str]
    metadata: List[str]


class TemplateImportRequest(BaseModel):
    """Request to import a global template (deprecated - templates now org/user scoped)."""
    # Using str instead of UUID for flexibility with external systems
    target_organization_id: Optional[str] = Field(None, max_length=100, description="Organization to import to")
    target_user_id: Optional[str] = Field(None, max_length=100, description="User to import to (requires organization)")
    new_name_fr: Optional[str] = Field(None, min_length=1, max_length=255, description="New French name")
    new_name_en: Optional[str] = Field(None, max_length=255, description="New English name")

    @model_validator(mode='after')
    def validate_user_requires_org(self):
        """Validate that user_id requires organization_id."""
        if self.target_user_id is not None and self.target_organization_id is None:
            raise ValueError("target_user_id requires target_organization_id to be set")
        return self


class ExportPreviewRequest(BaseModel):
    """Request for export preview."""
    template_id: Optional[UUID] = None


class PlaceholderStatus(BaseModel):
    """Status of a placeholder for export."""
    name: str
    status: Literal['available', 'missing', 'extraction_required']
    value: Optional[str] = None


class ExportPreviewResponse(BaseModel):
    """Response for export preview."""
    template_id: UUID
    template_name: str
    placeholders: List[PlaceholderStatus]
    extraction_required: bool
    estimated_extraction_tokens: Optional[int] = None
