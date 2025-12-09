#!/usr/bin/env python3
"""Pydantic schemas for document templates."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class TemplateCreate(BaseModel):
    """Schema for creating a new document template."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    service_id: UUID
    is_default: bool = False


class TemplateUpdate(BaseModel):
    """Schema for updating a document template."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_default: Optional[bool] = None


class TemplateResponse(BaseModel):
    """Schema for document template response."""
    id: UUID
    name: str
    description: Optional[str]
    service_id: Optional[UUID]
    organization_id: Optional[UUID]
    file_name: str
    file_size: int
    mime_type: str
    placeholders: Optional[List[str]]
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Response schema for listing templates."""
    items: List[TemplateResponse]
    total: int


class PlaceholderInfo(BaseModel):
    """Information about available placeholders."""
    name: str
    source: str = Field(
        ...,
        description="Source of placeholder: 'standard', 'template', or 'metadata'"
    )
    description: Optional[str] = None


class AllPlaceholdersResponse(BaseModel):
    """Response with all available placeholders for document generation."""
    standard: List[PlaceholderInfo]
    template: List[str]
    metadata: List[str]


class TemplateImportRequest(BaseModel):
    """Request to import a global template to a service."""
    service_id: UUID = Field(..., description="Target service ID")
    new_name: Optional[str] = Field(None, min_length=1, max_length=255, description="New name for the imported template")
    organization_id: Optional[UUID] = Field(None, description="Organization scope")
