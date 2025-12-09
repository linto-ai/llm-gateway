#!/usr/bin/env python3
from pydantic import BaseModel, Field
from typing import Optional, Any, Generic, TypeVar, List
from math import ceil

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized pagination response format per API contract."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(cls, items: List[T], total: int, page: int, page_size: int):
        """Create paginated response with calculated total_pages."""
        total_pages = ceil(total / page_size) if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )


class ErrorDetail(BaseModel):
    """Error detail structure."""
    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Standard error response format."""
    error: ErrorDetail


class MessageResponse(BaseModel):
    """Generic message response for successful operations."""
    message: str
    flavor_id: Optional[str] = None
    service_id: Optional[str] = None
