"""HuggingFace Pydantic schemas."""
from pydantic import BaseModel
from typing import Optional


class HuggingFaceTokenizerResponse(BaseModel):
    """Response schema for HuggingFace tokenizer lookup."""

    tokenizer_class: Optional[str] = None
    tokenizer_name: Optional[str] = None
    repo_path: str
    found: bool
    error: Optional[str] = None
