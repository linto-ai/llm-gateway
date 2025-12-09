#!/usr/bin/env python3
"""API router for flavor presets CRUD operations."""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Form, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.services.preset_service import preset_service
from app.services.flavor_service import FlavorService
from app.schemas.flavor_preset import (
    FlavorPresetCreate,
    FlavorPresetUpdate,
    FlavorPresetResponse,
)
from app.schemas.service import ServiceFlavorCreate, ServiceFlavorResponse
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flavor-presets", tags=["Flavor Presets"])


@router.get("", response_model=List[FlavorPresetResponse])
async def list_presets(
    service_type: Optional[str] = Query(None, description="Filter by service type"),
    db: AsyncSession = Depends(get_db)
) -> List[FlavorPresetResponse]:
    """List all flavor presets, optionally filtered by service type."""
    return await preset_service.list_presets(db, service_type)


@router.get("/{preset_id}", response_model=FlavorPresetResponse)
async def get_preset(
    preset_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> FlavorPresetResponse:
    """Get a specific preset by ID."""
    return await preset_service.get_preset(db, preset_id)


@router.post("", response_model=FlavorPresetResponse, status_code=status.HTTP_201_CREATED)
async def create_preset(
    preset: FlavorPresetCreate,
    db: AsyncSession = Depends(get_db)
) -> FlavorPresetResponse:
    """Create a new flavor preset."""
    return await preset_service.create_preset(db, preset)


@router.patch("/{preset_id}", response_model=FlavorPresetResponse)
async def update_preset(
    preset_id: UUID,
    preset_update: FlavorPresetUpdate,
    db: AsyncSession = Depends(get_db)
) -> FlavorPresetResponse:
    """Update a preset. System presets can be modified but not deleted."""
    return await preset_service.update_preset(db, preset_id, preset_update)


@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preset(
    preset_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a preset. System presets cannot be deleted."""
    await preset_service.delete_preset(db, preset_id)


@router.post(
    "/{preset_id}/apply",
    response_model=ServiceFlavorResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}}
)
async def apply_preset_to_flavor(
    preset_id: UUID,
    service_id: UUID = Form(...),
    model_id: UUID = Form(...),
    flavor_name: str = Form(...),
    db: AsyncSession = Depends(get_db)
) -> ServiceFlavorResponse:
    """Create a new flavor by applying a preset's configuration."""
    from app.services.service_service import service_service

    # Get preset
    preset = await preset_service.get_preset(db, preset_id)

    # Verify service exists
    service = await service_service.get_service_by_id(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Build flavor data from preset config
    flavor_data = ServiceFlavorCreate(
        name=flavor_name,
        model_id=model_id,
        temperature=preset.config.get("temperature", 0.7),
        top_p=preset.config.get("top_p", 0.9),
        max_tokens=preset.config.get("max_tokens", 2048),
        is_default=False,
        output_type=preset.config.get("output_type", "text"),
        processing_mode=preset.config.get("processing_mode", "iterative"),
        create_new_turn_after=preset.config.get("create_new_turn_after"),
        summary_turns=preset.config.get("summary_turns"),
        max_new_turns=preset.config.get("max_new_turns"),
        reduce_summary=preset.config.get("reduce_summary", False),
        consolidate_summary=preset.config.get("consolidate_summary", False),
    )

    # Create flavor via existing service
    return await FlavorService.create_flavor(db, service_id, flavor_data)
