#!/usr/bin/env python3
"""
Pydantic schemas for tokenizer API endpoints.
"""

from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field


class TokenizerInfo(BaseModel):
    """Information about a locally stored tokenizer."""

    id: str = Field(..., description="Tokenizer ID (filesystem-safe format)")
    source_repo: str = Field(..., description="Original HuggingFace repo ID")
    type: Literal["huggingface", "tiktoken"] = Field(
        ..., description="Tokenizer type"
    )
    size_bytes: int = Field(..., description="Size in bytes")
    created_at: datetime = Field(..., description="When the tokenizer was downloaded")

    class Config:
        from_attributes = True


class TokenizerListResponse(BaseModel):
    """Response for listing local tokenizers."""

    tokenizers: List[TokenizerInfo] = Field(
        default_factory=list, description="List of local tokenizers"
    )
    storage_path: str = Field(..., description="Path to tokenizer storage directory")
    total_size_bytes: int = Field(..., description="Total size of all tokenizers")


class TokenizerPreloadResponse(BaseModel):
    """Response for tokenizer preload operation."""

    success: bool = Field(..., description="Whether preload succeeded")
    model_identifier: str = Field(..., description="Model identifier")
    tokenizer_id: str = Field(..., description="Tokenizer ID or encoding name")
    tokenizer_type: Literal["huggingface", "tiktoken"] = Field(
        ..., description="Tokenizer type"
    )
    cached: bool = Field(
        ..., description="Whether tokenizer was already cached"
    )
    message: str = Field(..., description="Status message")


class TokenizerDeleteResponse(BaseModel):
    """Response for tokenizer deletion."""

    deleted: str = Field(..., description="Deleted tokenizer ID")
    freed_bytes: int = Field(..., description="Bytes freed by deletion")
