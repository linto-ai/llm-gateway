#!/usr/bin/env python3
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, computed_field  # field_validator kept for SaveAsTemplateRequest
from datetime import datetime
from uuid import UUID

from app.schemas.prompt_type import PromptTypeResponse
from app.core.prompt_validation import count_placeholders


VALID_PROMPT_CATEGORIES = ['system', 'user']


class PromptBase(BaseModel):
    """Base schema for prompts."""
    name: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)
    description: dict = Field(default_factory=dict)
    service_type: str = Field(..., description="Service type (required)")


class CreatePrompt(PromptBase):
    """Schema for creating a new prompt."""
    # Free-form organization identifier (any string up to 100 chars)
    organization_id: Optional[str] = None
    prompt_category: Literal['system', 'user'] = Field(..., description="How prompt is used: 'system' or 'user'")
    prompt_type: Optional[str] = Field('standard', description="Prompt type code: 'standard', 'reduce', or custom")


class UpdatePrompt(BaseModel):
    """Schema for updating a prompt (partial update)."""
    content: Optional[str] = Field(None, min_length=1)
    description: Optional[dict] = None
    service_type: Optional[str] = Field(None, description="Service type")
    prompt_category: Optional[Literal['system', 'user']] = Field(None, description="How prompt is used: 'system' or 'user'")
    prompt_type: Optional[str] = Field(None, description="Prompt type code: 'standard', 'reduce', or custom")


class PromptResponse(PromptBase):
    """Schema for prompt response."""
    id: UUID
    # Free-form organization identifier (any string up to 100 chars)
    organization_id: Optional[str]

    # Category field
    prompt_category: Literal['system', 'user']
    # Prompt type: full object instead of string (replaces prompt_role)
    prompt_type: Optional[PromptTypeResponse] = None
    parent_template_id: Optional[UUID] = None

    # Service type inherited from PromptBase (required, non-null)

    created_at: datetime
    updated_at: datetime

    # Computed field: number of {} placeholders in content
    # Used by frontend to filter prompts by processing mode:
    # - single_pass: requires 1 placeholder
    # - iterative: requires 2 placeholders
    @computed_field
    @property
    def placeholder_count(self) -> int:
        """Count {} placeholders in prompt content."""
        return count_placeholders(self.content)

    class Config:
        from_attributes = True


class DuplicatePrompt(BaseModel):
    """Schema for duplicating a prompt."""
    new_name: str = Field(..., min_length=1, max_length=100)
    # Free-form organization identifier (any string up to 100 chars)
    organization_id: Optional[str] = None


class SaveAsTemplateRequest(BaseModel):
    """Request to save prompt as template."""
    template_name: str = Field(..., min_length=1, max_length=100)
    category: Literal['system', 'user'] = Field(..., description="How prompt is used: 'system' or 'user'")
    prompt_type: Optional[str] = Field(None, description="Prompt type code: 'standard', 'reduce', or custom")
    description: Optional[dict] = Field(default_factory=dict)

    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        """Validate i18n keys."""
        if v:
            allowed_keys = {'en', 'fr'}
            if not all(k in allowed_keys for k in v.keys()):
                raise ValueError(f"Only {allowed_keys} language keys allowed")
        return v


# PromptListResponse removed - use PaginatedResponse[PromptResponse] from common.py
