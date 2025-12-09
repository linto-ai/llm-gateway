#!/usr/bin/env python3
"""API routes for prompt type management (CRUD)."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_db
from app.models.prompt_type import PromptType
from app.models.service_type import ServiceType
from app.models.prompt import Prompt
from app.schemas.prompt_type import (
    CreatePromptType,
    UpdatePromptType,
    PromptTypeResponse,
)

router = APIRouter(prefix="/prompt-types", tags=["Prompt Types"])


@router.get("", response_model=List[PromptTypeResponse])
async def list_prompt_types(
    active_only: bool = Query(False, description="Filter to active types only"),
    service_type: Optional[str] = Query(None, description="Filter by service type code"),
    db: AsyncSession = Depends(get_db)
) -> List[PromptTypeResponse]:
    """List all prompt types.

    - **active_only**: Filter to active types only (default: false)
    - **service_type**: Filter by service type code (e.g., 'summary', 'translation')
    """
    query = (
        select(PromptType)
        .options(selectinload(PromptType.service_type))
        .order_by(PromptType.display_order, PromptType.code)
    )

    if active_only:
        query = query.where(PromptType.is_active)

    if service_type:
        query = query.join(ServiceType).where(ServiceType.code == service_type)

    result = await db.execute(query)
    prompt_types = result.scalars().all()

    return [PromptTypeResponse.model_validate(pt) for pt in prompt_types]


@router.post("", response_model=PromptTypeResponse, status_code=201)
async def create_prompt_type(
    data: CreatePromptType,
    db: AsyncSession = Depends(get_db)
) -> PromptTypeResponse:
    """Create a new prompt type.

    - **code**: Unique code (lowercase, snake_case)
    - **name**: i18n names {en, fr}
    - **description**: Optional i18n descriptions
    - **is_active**: Whether the type is active (default: true)
    - **display_order**: Display order (default: 0)
    - **service_type_id**: Optional link to a service type
    """
    try:
        # Validate service_type_id if provided
        if data.service_type_id:
            st_result = await db.execute(
                select(ServiceType).where(ServiceType.id == data.service_type_id)
            )
            if not st_result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Invalid service_type_id")

        prompt_type = PromptType(
            code=data.code,
            name=data.name,
            description=data.description,
            is_system=False,
            is_active=data.is_active,
            display_order=data.display_order,
            service_type_id=data.service_type_id,
        )

        db.add(prompt_type)
        await db.commit()

        # Reload with relationship
        result = await db.execute(
            select(PromptType)
            .options(selectinload(PromptType.service_type))
            .where(PromptType.id == prompt_type.id)
        )
        prompt_type = result.scalar_one()

        return PromptTypeResponse.model_validate(prompt_type)

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Prompt type with code '{data.code}' already exists"
        )


@router.get("/{prompt_type_id}", response_model=PromptTypeResponse)
async def get_prompt_type(
    prompt_type_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> PromptTypeResponse:
    """Get prompt type by ID."""
    result = await db.execute(
        select(PromptType)
        .options(selectinload(PromptType.service_type))
        .where(PromptType.id == prompt_type_id)
    )
    prompt_type = result.scalar_one_or_none()

    if not prompt_type:
        raise HTTPException(status_code=404, detail="Prompt type not found")

    return PromptTypeResponse.model_validate(prompt_type)


@router.patch("/{prompt_type_id}", response_model=PromptTypeResponse)
async def update_prompt_type(
    prompt_type_id: UUID,
    data: UpdatePromptType,
    db: AsyncSession = Depends(get_db)
) -> PromptTypeResponse:
    """Update a prompt type.

    - **name**: Updated i18n names
    - **description**: Updated i18n descriptions
    - **is_active**: Whether the type is active
    - **display_order**: Display order
    - **service_type_id**: Optional link to a service type
    """
    result = await db.execute(
        select(PromptType).where(PromptType.id == prompt_type_id)
    )
    prompt_type = result.scalar_one_or_none()

    if not prompt_type:
        raise HTTPException(status_code=404, detail="Prompt type not found")

    # Validate service_type_id if provided
    if data.service_type_id is not None:
        st_result = await db.execute(
            select(ServiceType).where(ServiceType.id == data.service_type_id)
        )
        if not st_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Invalid service_type_id")

    # Update fields
    if data.name is not None:
        prompt_type.name = data.name
    if data.description is not None:
        prompt_type.description = data.description
    if data.is_active is not None:
        prompt_type.is_active = data.is_active
    if data.display_order is not None:
        prompt_type.display_order = data.display_order
    if data.service_type_id is not None:
        prompt_type.service_type_id = data.service_type_id

    await db.commit()

    # Reload with relationship
    result = await db.execute(
        select(PromptType)
        .options(selectinload(PromptType.service_type))
        .where(PromptType.id == prompt_type_id)
    )
    prompt_type = result.scalar_one()

    return PromptTypeResponse.model_validate(prompt_type)


@router.delete("/{prompt_type_id}", status_code=204)
async def delete_prompt_type(
    prompt_type_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a prompt type (non-system only).

    Returns:
    - **204 No Content**: Successfully deleted
    - **403 Forbidden**: Cannot delete system type
    - **404 Not Found**: Prompt type not found
    - **409 Conflict**: Prompt type is referenced by prompts
    """
    result = await db.execute(
        select(PromptType).where(PromptType.id == prompt_type_id)
    )
    prompt_type = result.scalar_one_or_none()

    if not prompt_type:
        raise HTTPException(status_code=404, detail="Prompt type not found")

    if prompt_type.is_system:
        raise HTTPException(
            status_code=403,
            detail="Cannot delete system prompt type"
        )

    # Check if referenced by any prompts
    ref_result = await db.execute(
        select(Prompt).where(Prompt.prompt_type_id == prompt_type_id).limit(1)
    )
    if ref_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Cannot delete prompt type: referenced by prompts"
        )

    await db.delete(prompt_type)
    await db.commit()
