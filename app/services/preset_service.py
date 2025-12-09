#!/usr/bin/env python3
"""Business logic for flavor preset management."""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.flavor_preset import FlavorPreset
from app.schemas.flavor_preset import FlavorPresetCreate, FlavorPresetUpdate
from app.core.service_types import get_service_type_config


def validate_preset_config(service_type: str, config: dict) -> List[str]:
    """Validate preset config against service type requirements.

    Args:
        service_type: The service type identifier
        config: The preset configuration dict

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    type_config = get_service_type_config(service_type)

    if not type_config:
        errors.append(f"Unknown service type: {service_type}")
        return errors

    # Check reduce-related fields
    if not type_config.supports_reduce:
        if config.get("reduce_summary"):
            errors.append(f"Service type '{service_type}' does not support reduce_summary")

    # Check chunking-related fields
    if not type_config.supports_chunking:
        if config.get("processing_mode") == "iterative":
            errors.append(f"Service type '{service_type}' does not support iterative processing")

    return errors


class PresetService:
    """Service for managing flavor presets."""

    @staticmethod
    async def list_presets(
        db: AsyncSession,
        service_type: Optional[str] = None
    ) -> List[FlavorPreset]:
        """List all presets, optionally filtered by service_type."""
        query = select(FlavorPreset).where(FlavorPreset.is_active)
        if service_type:
            query = query.where(FlavorPreset.service_type == service_type)
        query = query.order_by(FlavorPreset.name)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_preset(db: AsyncSession, preset_id: UUID) -> FlavorPreset:
        """Get a preset by ID."""
        result = await db.execute(
            select(FlavorPreset).where(FlavorPreset.id == preset_id)
        )
        preset = result.scalar_one_or_none()
        if not preset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Preset not found"
            )
        return preset

    @staticmethod
    async def create_preset(
        db: AsyncSession,
        data: FlavorPresetCreate
    ) -> FlavorPreset:
        """Create a new preset."""
        # Validate config against service type
        errors = validate_preset_config(data.service_type, data.config)
        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"errors": errors}
            )

        # Check for duplicate name
        existing = await db.execute(
            select(FlavorPreset).where(FlavorPreset.name == data.name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Preset name already exists"
            )

        preset = FlavorPreset(**data.model_dump())
        db.add(preset)
        await db.commit()
        await db.refresh(preset)
        return preset

    @staticmethod
    async def update_preset(
        db: AsyncSession,
        preset_id: UUID,
        data: FlavorPresetUpdate
    ) -> FlavorPreset:
        """Update a preset."""
        preset = await PresetService.get_preset(db, preset_id)

        update_data = data.model_dump(exclude_unset=True)

        # Validate if config or service_type changed
        if 'config' in update_data or 'service_type' in update_data:
            service_type = update_data.get('service_type', preset.service_type)
            config = update_data.get('config', preset.config)
            errors = validate_preset_config(service_type, config)
            if errors:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"errors": errors}
                )

        for field, value in update_data.items():
            setattr(preset, field, value)

        await db.commit()
        await db.refresh(preset)
        return preset

    @staticmethod
    async def delete_preset(db: AsyncSession, preset_id: UUID) -> None:
        """Delete a preset. System presets cannot be deleted."""
        preset = await PresetService.get_preset(db, preset_id)

        if preset.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete system preset"
            )

        await db.delete(preset)
        await db.commit()


preset_service = PresetService()
