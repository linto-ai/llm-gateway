#!/usr/bin/env python3
"""Schemas for chat completions endpoint."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID


class ChatMessage(BaseModel):
    """A single chat message (user or assistant only)."""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=100000)


class ChatContext(BaseModel):
    """Context injected into the system prompt template."""
    transcript: str = Field(..., min_length=1, max_length=500000)
    summary: Optional[str] = Field(None, max_length=100000)
    metadata: Optional[Dict[str, Any]] = None


class ChatCompletionRequest(BaseModel):
    """Request body for POST /chat/completions."""
    flavor_id: UUID
    messages: List[ChatMessage] = Field(..., min_length=1, max_length=100)
    context: ChatContext
    max_tokens: Optional[int] = Field(None, ge=1, le=128000)
    session_id: Optional[str] = Field(None, max_length=255)
    organization_id: Optional[str] = Field(None, max_length=100)


class ChatTokenUsage(BaseModel):
    """Token usage statistics from the provider."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatTokenEvent(BaseModel):
    """SSE token event payload."""
    content: str


class ChatDoneEvent(BaseModel):
    """SSE done event payload."""
    usage: ChatTokenUsage


class ChatErrorEvent(BaseModel):
    """SSE error event payload."""
    error: str
