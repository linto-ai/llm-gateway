#!/usr/bin/env python3
"""API routes for prompt management."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_db
from app.services import prompt_service
from app.schemas.prompt import (
    SaveAsTemplateRequest,
    CreatePrompt,
    UpdatePrompt,
    PromptResponse,
    DuplicatePrompt,
)
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/prompts", tags=["Prompts"])


@router.post("", response_model=PromptResponse, status_code=201)
async def create_prompt(
    data: CreatePrompt,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new prompt.

    - **name**: Unique name (max 100 chars)
    - **content**: Prompt content (required)
    - **description**: i18n descriptions (optional)
    - **service_type**: Service type (required) - validated against database
    - **prompt_type**: Prompt type code (e.g., 'standard', 'reduce') - validated against database
    - **organization_id**: UUID or null for global prompt
    """
    try:
        prompt = await prompt_service.create_prompt(db, data)
        return prompt
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Duplicate prompt: same name and organization already exists"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=PaginatedResponse[PromptResponse])
async def list_prompts(
    organization_id: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    service_type: Optional[str] = Query(None, description="Filter by service type"),
    prompt_category: Optional[str] = Query(None, description="Filter: 'system' or 'user'"),
    prompt_type: Optional[str] = Query(None, description="Filter by prompt type code (e.g., 'standard', 'reduce')"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List prompts with optional filters.

    - **organization_id**: Filter by organization UUID
    - **name**: Partial match (case-insensitive)
    - **service_type**: Filter by service type
    - **prompt_category**: Filter by category ('system' or 'user')
    - **prompt_type**: Filter by prompt type code (e.g., 'standard', 'reduce')
    - **page**: Page number (default 1)
    - **page_size**: Items per page (max 100, default 20)
    """
    offset = (page - 1) * page_size
    prompts, total = await prompt_service.list_prompts(
        db,
        organization_id=organization_id,
        name=name,
        service_type=service_type,
        prompt_category=prompt_category,
        prompt_type=prompt_type,
        limit=page_size,
        offset=offset
    )

    return PaginatedResponse.create(
        items=prompts,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/templates", response_model=PaginatedResponse[PromptResponse])
async def list_templates(
    category: Optional[str] = Query(None, description="Filter by prompt_category ('system' or 'user')"),
    prompt_type: Optional[str] = Query(None, description="Filter by prompt type code (e.g., 'standard', 'reduce')"),
    service_type: Optional[str] = Query(None, description="Filter by service type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """
    List prompt templates with filtering.

    Note: All prompts are now templates (is_template column removed).

    - **category**: Filter by prompt_category ('system' or 'user')
    - **prompt_type**: Filter by prompt type code (e.g., 'standard', 'reduce')
    - **service_type**: Filter by service type
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 50, max: 100)
    """
    result = await prompt_service.list_templates(
        db,
        category=category,
        prompt_type=prompt_type,
        service_type=service_type,
        page=page,
        page_size=page_size
    )

    return PaginatedResponse.create(
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"]
    )


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get prompt by ID."""
    prompt = await prompt_service.get_prompt(db, prompt_id)

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    return prompt


@router.patch("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: str,
    data: UpdatePrompt,
    db: AsyncSession = Depends(get_db)
):
    """
    Update prompt content and/or description.

    Note: Creates a new service version if the prompt is referenced by any service.
    """
    prompt = await prompt_service.update_prompt(db, prompt_id, data)

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    return prompt


@router.delete("/{prompt_id}", status_code=204)
async def delete_prompt(
    prompt_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a prompt.

    Returns 409 if the prompt is referenced by any service flavors.
    """
    try:
        deleted = await prompt_service.delete_prompt(db, prompt_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Prompt not found")

    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{prompt_id}/duplicate", response_model=PromptResponse, status_code=201)
async def duplicate_prompt(
    prompt_id: str,
    data: DuplicatePrompt,
    db: AsyncSession = Depends(get_db)
):
    """
    Duplicate a prompt with a new name.

    - **new_name**: Name for the duplicated prompt (required)
    - **organization_id**: Target organization (optional)
    """
    try:
        prompt = await prompt_service.duplicate_prompt(db, prompt_id, data)

        if not prompt:
            raise HTTPException(status_code=404, detail="Source prompt not found")

        return prompt

    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Duplicate name in target organization"
        )


@router.post("/{prompt_id}/save-as-template", response_model=PromptResponse, status_code=201)
async def save_as_template(
    prompt_id: str,
    request: SaveAsTemplateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Save prompt as reusable template.

    Creates a template copy of the prompt for reuse across services.

    - **template_name**: Name for the template (required, max 100 chars)
    - **category**: Prompt category ('system' or 'user')
    - **prompt_type**: Optional prompt type code (e.g., 'standard', 'reduce')
    - **description**: Optional i18n description (en, fr keys allowed)
    """
    try:
        template = await prompt_service.save_as_template(
            db,
            prompt_id=prompt_id,
            template_name=request.template_name,
            category=request.category,
            prompt_type=request.prompt_type,
            description=request.description
        )
        return template

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Template name already exists")
