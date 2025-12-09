#!/usr/bin/env python3
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal, Union
from datetime import datetime
from uuid import UUID


class ModelBase(BaseModel):
    """Base schema for Model with common fields."""
    model_name: str = Field(..., min_length=1, max_length=200)
    model_identifier: str = Field(..., min_length=1, max_length=200)
    context_length: int = Field(..., gt=0)
    max_generation_length: int = Field(..., gt=0)
    tokenizer_class: Optional[str] = Field(None, max_length=100)
    tokenizer_name: Optional[str] = Field(None, max_length=200)
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # Extended fields
    huggingface_repo: Optional[str] = Field(None, max_length=500)
    security_level: Optional[str] = Field(None, max_length=50)
    deployment_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    best_use: Optional[str] = None
    usage_type: Optional[str] = Field(None, max_length=50)
    system_prompt: Optional[str] = None


class ModelCreate(ModelBase):
    """Schema for creating a new model."""
    provider_id: UUID


class ModelUpdate(BaseModel):
    """Schema for updating an existing model."""
    model_name: Optional[str] = Field(None, min_length=1, max_length=200)
    model_identifier: Optional[str] = Field(None, min_length=1, max_length=200)
    context_length: Optional[int] = Field(None, gt=0)
    max_generation_length: Optional[int] = Field(None, gt=0)
    tokenizer_class: Optional[str] = Field(None, max_length=100)
    tokenizer_name: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None
    # Extended fields
    huggingface_repo: Optional[str] = Field(None, max_length=500)
    security_level: Optional[str] = Field(None, max_length=50)
    deployment_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    best_use: Optional[str] = None
    usage_type: Optional[str] = Field(None, max_length=50)
    system_prompt: Optional[str] = None


class ModelResponse(ModelBase):
    """Schema for model response with database fields."""
    id: UUID
    provider_id: UUID
    provider_name: Optional[str] = None

    # Health monitoring fields
    health_status: Literal['available', 'unavailable', 'unknown', 'error'] = 'unknown'
    health_checked_at: Optional[datetime] = None
    health_error: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelListResponse(BaseModel):
    """Response schema for paginated model list (internal use)."""
    total: int
    items: List[ModelResponse]


class ModelVerificationResponse(BaseModel):
    """Response from model verification endpoint."""
    model_id: UUID
    health_status: Literal['available', 'unavailable', 'unknown', 'error']
    checked_at: datetime
    error: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class DiscoveredModel(BaseModel):
    """Model discovered from provider API."""
    model_identifier: str = Field(..., max_length=200)
    model_name: str = Field(..., max_length=200)
    context_length: int = Field(..., gt=0)
    max_generation_length: int = Field(..., gt=0)
    tokenizer_class: Optional[str] = Field(None, max_length=100)
    tokenizer_name: Optional[str] = Field(None, max_length=200)
    available: bool = True
    # Extended fields from provider API
    description: Optional[str] = None
    best_use: Optional[str] = None
    sensitivity_level: Optional[Union[str, List[str]]] = None  # Can be string or list from different providers
    default_for: Optional[List[str]] = None
    usage_type: Optional[str] = Field(None, max_length=50)
    system_prompt: Optional[str] = None
    deployment_name: Optional[str] = Field(None, max_length=200)
    custom_tokenizer: Optional[str] = Field(None, max_length=200)
    metadata: Optional[Dict[str, Any]] = None


class ModelVerificationResult(BaseModel):
    """Schema for a single model verification result."""
    model_id: UUID
    model_identifier: str
    status: str  # "available" | "unavailable" | "error"
    error_message: Optional[str] = None


class ProviderModelsVerificationResponse(BaseModel):
    """Response for provider-wide model verification (all models for a provider)."""
    provider_id: UUID
    total_models: int
    verified_count: int
    failed_count: int
    results: List[ModelVerificationResult]
    verified_at: datetime


class ModelLimitsResponse(BaseModel):
    """Response for /models/{id}/limits endpoint."""
    model_id: UUID
    model_name: str
    model_identifier: str
    context_length: int
    max_generation_length: int
    available_for_input: int
