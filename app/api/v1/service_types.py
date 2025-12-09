#!/usr/bin/env python3
"""API routes for service type management (database-driven CRUD)."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_db
from app.models.service_type import ServiceType
from app.models.prompt import Prompt
from app.schemas.service_type import (
    CreateServiceType,
    UpdateServiceType,
    ServiceTypeResponse,
)

router = APIRouter(prefix="/service-types", tags=["Service Types"])


@router.get("", response_model=List[ServiceTypeResponse])
async def list_service_types(
    active_only: bool = Query(False, description="Filter to active types only"),
    db: AsyncSession = Depends(get_db)
) -> List[ServiceTypeResponse]:
    """List all service types.

    - **active_only**: Filter to active types only (default: false)
    """
    query = select(ServiceType).order_by(ServiceType.display_order, ServiceType.code)

    if active_only:
        query = query.where(ServiceType.is_active)

    result = await db.execute(query)
    service_types = result.scalars().all()

    return [ServiceTypeResponse.model_validate(st) for st in service_types]


@router.post("", response_model=ServiceTypeResponse, status_code=201)
async def create_service_type(
    data: CreateServiceType,
    db: AsyncSession = Depends(get_db)
) -> ServiceTypeResponse:
    """Create a new service type.

    - **code**: Unique code (lowercase, snake_case)
    - **name**: i18n names {en, fr}
    - **description**: Optional i18n descriptions
    - **is_active**: Whether the type is active (default: true)
    - **display_order**: Display order (default: 0)
    """
    try:
        service_type = ServiceType(
            code=data.code,
            name=data.name,
            description=data.description,
            is_system=False,
            is_active=data.is_active,
            display_order=data.display_order,
        )

        db.add(service_type)
        await db.commit()
        await db.refresh(service_type)

        return ServiceTypeResponse.model_validate(service_type)

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Service type with code '{data.code}' already exists"
        )


@router.get("/{service_type_id}", response_model=ServiceTypeResponse)
async def get_service_type(
    service_type_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> ServiceTypeResponse:
    """Get service type by ID."""
    result = await db.execute(
        select(ServiceType).where(ServiceType.id == service_type_id)
    )
    service_type = result.scalar_one_or_none()

    if not service_type:
        raise HTTPException(status_code=404, detail="Service type not found")

    return ServiceTypeResponse.model_validate(service_type)


@router.patch("/{service_type_id}", response_model=ServiceTypeResponse)
async def update_service_type(
    service_type_id: UUID,
    data: UpdateServiceType,
    db: AsyncSession = Depends(get_db)
) -> ServiceTypeResponse:
    """Update a service type.

    - **name**: Updated i18n names
    - **description**: Updated i18n descriptions
    - **is_active**: Whether the type is active
    - **display_order**: Display order
    """
    result = await db.execute(
        select(ServiceType).where(ServiceType.id == service_type_id)
    )
    service_type = result.scalar_one_or_none()

    if not service_type:
        raise HTTPException(status_code=404, detail="Service type not found")

    # Update fields
    if data.name is not None:
        service_type.name = data.name
    if data.description is not None:
        service_type.description = data.description
    if data.is_active is not None:
        service_type.is_active = data.is_active
    if data.display_order is not None:
        service_type.display_order = data.display_order

    await db.commit()
    await db.refresh(service_type)

    return ServiceTypeResponse.model_validate(service_type)


@router.delete("/{service_type_id}", status_code=204)
async def delete_service_type(
    service_type_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a service type (non-system only).

    Returns:
    - **204 No Content**: Successfully deleted
    - **403 Forbidden**: Cannot delete system type
    - **404 Not Found**: Service type not found
    - **409 Conflict**: Service type is referenced by prompts or services
    """
    result = await db.execute(
        select(ServiceType).where(ServiceType.id == service_type_id)
    )
    service_type = result.scalar_one_or_none()

    if not service_type:
        raise HTTPException(status_code=404, detail="Service type not found")

    if service_type.is_system:
        raise HTTPException(
            status_code=403,
            detail="Cannot delete system service type"
        )

    # Check if referenced by any prompts (via service_type code)
    ref_result = await db.execute(
        select(Prompt).where(Prompt.service_type == service_type.code).limit(1)
    )
    if ref_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Cannot delete service type: referenced by prompts"
        )

    await db.delete(service_type)
    await db.commit()
