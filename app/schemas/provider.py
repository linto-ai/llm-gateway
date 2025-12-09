from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator

class CreateProviderRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider_type: str = Field(..., pattern="^(openai|anthropic|cohere|openrouter|custom)$")
    api_base_url: str = Field(..., min_length=1, max_length=500)
    api_key: str = Field(..., min_length=1, max_length=2000)
    security_level: str = Field(default="sensitive", pattern="^(secure|sensitive|insecure)$")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('api_base_url')
    def validate_url(cls, v):
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('API base URL must start with http:// or https://')
        return v

class UpdateProviderRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    api_base_url: Optional[str] = Field(None, min_length=1, max_length=500)
    api_key: Optional[str] = Field(None, min_length=1, max_length=2000)
    security_level: Optional[str] = Field(None, pattern="^(secure|sensitive|insecure)$")
    metadata: Optional[Dict[str, Any]] = None

    @validator('api_base_url')
    def validate_url(cls, v):
        if v is not None and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('API base URL must start with http:// or https://')
        return v


class ProviderResponse(BaseModel):
    id: UUID
    name: str
    provider_type: str
    api_base_url: str
    api_key_exists: bool
    security_level: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True

# ListProvidersResponse removed - use PaginatedResponse[ProviderResponse] from common.py

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail
