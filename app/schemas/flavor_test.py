#!/usr/bin/env python3
"""Pydantic schemas for flavor testing functionality."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class FlavorTestRequest(BaseModel):
    """Request schema for testing a flavor configuration."""

    prompt: str = Field(..., min_length=1, description="Test prompt to send to model")
    max_tokens: Optional[int] = Field(None, gt=0, description="Override flavor's max_tokens for this test")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Write a short poem about AI",
                "max_tokens": 100
            }
        }


class FlavorTestResponse(BaseModel):
    """Response schema for flavor test execution."""

    flavor_id: UUID
    flavor_name: str
    model: Dict[str, str]  # model_name, model_identifier, provider_name
    request: Dict[str, Any]  # Sent parameters
    response: Dict[str, str]  # content, finish_reason
    metadata: Dict[str, Any]  # tokens, latency, cost
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "flavor_id": "123e4567-e89b-12d3-a456-426614174000",
                "flavor_name": "gpt-4-default",
                "model": {
                    "model_name": "GPT-4",
                    "model_identifier": "gpt-4",
                    "provider_name": "OpenAI"
                },
                "request": {
                    "prompt": "Write a short poem about AI",
                    "temperature": 0.7,
                    "max_tokens": 100,
                    "top_p": 0.9,
                    "frequency_penalty": 0.0,
                    "presence_penalty": 0.0,
                    "stop_sequences": []
                },
                "response": {
                    "content": "In silicon dreams, thoughts arise...",
                    "finish_reason": "stop"
                },
                "metadata": {
                    "input_tokens": 8,
                    "output_tokens": 42,
                    "total_tokens": 50,
                    "latency_ms": 1234,
                    "estimated_cost": 0.00075
                },
                "timestamp": "2025-11-25T10:30:00Z"
            }
        }
