#!/usr/bin/env python3
"""Synthetic conversation templates API."""

from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["synthetic-templates"])

# Templates directory relative to project root
TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "tests/data/conversations/synthetic"


class SyntheticTemplate(BaseModel):
    """Schema for a synthetic template entry."""

    filename: str
    language: str
    error_type: str
    description: str
    size_bytes: int


class SyntheticTemplatesResponse(BaseModel):
    """Response schema for list of synthetic templates."""

    templates: List[SyntheticTemplate]


class SyntheticTemplateContent(BaseModel):
    """Response schema for synthetic template content."""

    filename: str
    content: str
    language: str
    error_type: str


# Human-readable descriptions for each template type
DESCRIPTIONS = {
    ("en", "perfect"): "English conversation - Ground truth baseline",
    ("en", "diarization_errors"): "English conversation - Sentence splits across speakers",
    ("en", "full_errors"): "English conversation - Diarization + speaker label errors",
    ("fr", "perfect"): "French conversation - Ground truth baseline",
    ("fr", "diarization_errors"): "French conversation - Sentence splits across speakers",
    ("fr", "full_errors"): "French conversation - Diarization + speaker label errors",
    ("mixed", "perfect"): "Mixed EN/FR conversation - Ground truth baseline",
    ("mixed", "diarization_errors"): "Mixed EN/FR conversation - Sentence splits across speakers",
    ("mixed", "full_errors"): "Mixed EN/FR conversation - Diarization + speaker label errors",
}


def parse_template_filename(filename: str) -> tuple:
    """
    Parse language and error_type from filename.

    Expected format: {lang}_{error_type}.txt
    Examples: en_perfect.txt, fr_diarization_errors.txt

    Args:
        filename: Template filename

    Returns:
        Tuple of (language, error_type)
    """
    name = filename.replace(".txt", "")
    parts = name.split("_", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return "unknown", "unknown"


@router.get(
    "/synthetic-templates",
    response_model=SyntheticTemplatesResponse,
    summary="List synthetic templates",
    description="List available synthetic conversation templates for service testing.",
)
async def list_synthetic_templates() -> SyntheticTemplatesResponse:
    """
    List available synthetic conversation templates.

    Templates are conversation transcripts used for testing summarization services
    with known input characteristics (language, error types).

    Returns:
        List of template metadata including filename, language, error type, and size
    """
    templates = []

    if not TEMPLATES_DIR.exists():
        return SyntheticTemplatesResponse(templates=[])

    for f in TEMPLATES_DIR.iterdir():
        if f.suffix == ".txt" and f.is_file():
            lang, error_type = parse_template_filename(f.name)
            templates.append(
                SyntheticTemplate(
                    filename=f.name,
                    language=lang,
                    error_type=error_type,
                    description=DESCRIPTIONS.get(
                        (lang, error_type), f"Synthetic conversation: {f.name}"
                    ),
                    size_bytes=f.stat().st_size,
                )
            )

    # Sort by language, then error_type for consistent ordering
    templates.sort(key=lambda t: (t.language, t.error_type))

    return SyntheticTemplatesResponse(templates=templates)


@router.get(
    "/synthetic-templates/{filename}/content",
    response_model=SyntheticTemplateContent,
    summary="Get template content",
    description="Get the content of a specific synthetic template file.",
    responses={
        404: {"description": "Template not found"},
        400: {"description": "Invalid template file"},
    },
)
async def get_template_content(filename: str) -> SyntheticTemplateContent:
    """
    Get content of a synthetic template.

    Args:
        filename: Template filename (e.g., "en_perfect.txt")

    Returns:
        Template content with metadata

    Raises:
        HTTPException: 404 if template not found, 400 if invalid file type
    """
    # Security: validate filename to prevent path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = TEMPLATES_DIR / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Template '{filename}' not found")

    if file_path.suffix != ".txt":
        raise HTTPException(status_code=400, detail="Invalid template file type")

    lang, error_type = parse_template_filename(filename)
    content = file_path.read_text(encoding="utf-8")

    return SyntheticTemplateContent(
        filename=filename,
        content=content,
        language=lang,
        error_type=error_type,
    )
