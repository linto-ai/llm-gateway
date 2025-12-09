#!/usr/bin/env python3
"""API router for service flavor management."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.core.prompt_validation import (
    count_placeholders,
    get_required_placeholders
)
from app.services.flavor_service import FlavorService
from app.services.flavor_test_service import FlavorTestService
from app.services.flavor_analytics_service import FlavorAnalyticsService
from app.schemas.service import (
    ServiceFlavorResponse,
    ServiceFlavorUpdate,
    ServiceFlavorListResponse,
    PromptValidationRequest,
    PromptValidationResponse
)
from app.schemas.flavor_test import FlavorTestRequest, FlavorTestResponse
from app.schemas.flavor_analytics import FlavorStats, FlavorUsageHistory
from app.schemas.common import MessageResponse


router = APIRouter(tags=["Service Flavors"])


@router.get("/services/{service_id}/flavors", response_model=ServiceFlavorListResponse)
async def list_flavors(
    service_id: UUID,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    include_stats: bool = Query(False, description="Include usage statistics"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all flavors for a service with optional filtering.

    - **service_id**: Service UUID
    - **is_active**: Optional filter by active status
    - **include_stats**: Include usage statistics (not implemented yet)
    """
    items, total = await FlavorService.list_flavors(db, service_id, is_active=is_active)

    # Convert to response models with prompt names
    response_items = []
    for flavor in items:
        model_info = None
        if flavor.model:
            provider_name = flavor.model.provider.name if flavor.model.provider else "Unknown"
            model_info = {
                "id": flavor.model.id,
                "model_name": flavor.model.model_name,
                "model_identifier": flavor.model.model_identifier,
                "provider_id": flavor.model.provider_id,
                "provider_name": provider_name,
                "context_length": flavor.model.context_length,
                "max_generation_length": flavor.model.max_generation_length,
            }

        response_data = ServiceFlavorResponse.model_validate(flavor)
        response_data.model = model_info
        response_data.system_prompt_name = flavor.system_prompt.name if flavor.system_prompt else None
        response_data.user_prompt_template_name = flavor.user_prompt_template.name if flavor.user_prompt_template else None
        response_data.reduce_prompt_name = flavor.reduce_prompt.name if flavor.reduce_prompt else None
        response_data.placeholder_extraction_prompt_name = flavor.placeholder_extraction_prompt.name if flavor.placeholder_extraction_prompt else None
        response_data.categorization_prompt_name = flavor.categorization_prompt.name if flavor.categorization_prompt else None
        # Fallback flavor details
        if flavor.fallback_flavor:
            response_data.fallback_flavor_name = flavor.fallback_flavor.name
            response_data.fallback_service_name = flavor.fallback_flavor.service.name if flavor.fallback_flavor.service else None
        response_items.append(response_data)

    return ServiceFlavorListResponse(
        items=response_items,
        total=total
    )


@router.get("/flavors/{flavor_id}", response_model=ServiceFlavorResponse)
async def get_flavor(
    flavor_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get flavor details with model and provider information.

    - **flavor_id**: UUID of the flavor
    """
    flavor = await FlavorService.get_flavor(db, flavor_id)

    # Build ModelInfo with provider_name
    model_info = None
    if flavor.model:
        provider_name = flavor.model.provider.name if flavor.model.provider else "Unknown"
        model_info = {
            "id": flavor.model.id,
            "model_name": flavor.model.model_name,
            "model_identifier": flavor.model.model_identifier,
            "provider_id": flavor.model.provider_id,
            "provider_name": provider_name,
            "context_length": flavor.model.context_length,
            "max_generation_length": flavor.model.max_generation_length,
        }

    # Convert to response model with prompt names
    response_data = ServiceFlavorResponse.model_validate(flavor)
    response_data.model = model_info
    response_data.system_prompt_name = flavor.system_prompt.name if flavor.system_prompt else None
    response_data.user_prompt_template_name = flavor.user_prompt_template.name if flavor.user_prompt_template else None
    response_data.reduce_prompt_name = flavor.reduce_prompt.name if flavor.reduce_prompt else None
    response_data.placeholder_extraction_prompt_name = flavor.placeholder_extraction_prompt.name if flavor.placeholder_extraction_prompt else None
    response_data.categorization_prompt_name = flavor.categorization_prompt.name if flavor.categorization_prompt else None
    # Fallback flavor details
    if flavor.fallback_flavor:
        response_data.fallback_flavor_name = flavor.fallback_flavor.name
        response_data.fallback_service_name = flavor.fallback_flavor.service.name if flavor.fallback_flavor.service else None

    return response_data


@router.patch("/flavors/{flavor_id}", response_model=ServiceFlavorResponse)
async def update_flavor(
    flavor_id: UUID,
    flavor_update: ServiceFlavorUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update flavor configuration (partial update).

    - **flavor_id**: UUID of the flavor
    - **flavor_update**: Fields to update
    """
    flavor = await FlavorService.update_flavor(db, flavor_id, flavor_update)

    # Build ModelInfo with provider_name
    model_info = None
    if flavor.model:
        provider_name = flavor.model.provider.name if flavor.model.provider else "Unknown"
        model_info = {
            "id": flavor.model.id,
            "model_name": flavor.model.model_name,
            "model_identifier": flavor.model.model_identifier,
            "provider_id": flavor.model.provider_id,
            "provider_name": provider_name,
            "context_length": flavor.model.context_length,
            "max_generation_length": flavor.model.max_generation_length,
        }

    # Convert to response model with prompt names
    response_data = ServiceFlavorResponse.model_validate(flavor)
    response_data.model = model_info
    response_data.system_prompt_name = flavor.system_prompt.name if flavor.system_prompt else None
    response_data.user_prompt_template_name = flavor.user_prompt_template.name if flavor.user_prompt_template else None
    response_data.reduce_prompt_name = flavor.reduce_prompt.name if flavor.reduce_prompt else None
    response_data.placeholder_extraction_prompt_name = flavor.placeholder_extraction_prompt.name if flavor.placeholder_extraction_prompt else None
    response_data.categorization_prompt_name = flavor.categorization_prompt.name if flavor.categorization_prompt else None
    # Fallback flavor details
    if flavor.fallback_flavor:
        response_data.fallback_flavor_name = flavor.fallback_flavor.name
        response_data.fallback_service_name = flavor.fallback_flavor.service.name if flavor.fallback_flavor.service else None

    return response_data


@router.delete("/flavors/{flavor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flavor(
    flavor_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a flavor with safety checks.

    - **flavor_id**: UUID of the flavor

    **Constraints:**
    - Cannot delete default flavor
    - Cannot delete if has active jobs
    """
    await FlavorService.delete_flavor(db, flavor_id)


@router.post("/flavors/{flavor_id}/set-default", response_model=MessageResponse)
async def set_default_flavor(
    flavor_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Set flavor as default for its service.

    - **flavor_id**: UUID of the flavor

    **Requirements:**
    - Flavor must be active
    """
    flavor = await FlavorService.set_default_flavor(db, flavor_id)

    return MessageResponse(
        message="Flavor set as default successfully",
        flavor_id=str(flavor.id),
        service_id=str(flavor.service_id)
    )


@router.post("/flavors/{flavor_id}/test", response_model=FlavorTestResponse)
async def test_flavor(
    flavor_id: UUID,
    test_request: FlavorTestRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Test a flavor configuration with a sample prompt.

    - **flavor_id**: UUID of the flavor
    - **test_request**: Test prompt and optional overrides

    **Note:** No job record is created for test executions.
    """
    return await FlavorTestService.test_flavor(db, flavor_id, test_request)


@router.get("/flavors/{flavor_id}/stats", response_model=FlavorStats)
async def get_flavor_stats(
    flavor_id: UUID,
    period: str = Query('24h', regex='^(24h|7d|30d|all)$'),
    db: AsyncSession = Depends(get_db)
):
    """
    Get usage statistics for a flavor.

    - **flavor_id**: UUID of the flavor
    - **period**: Time period (24h, 7d, 30d, all)

    **Returns comprehensive metrics:**
    - Request counts and success rates
    - Token usage (input, output, total)
    - Latency statistics (avg, min, max, percentiles)
    - Cost analytics
    - Time series data
    """
    return await FlavorAnalyticsService.get_flavor_stats(db, flavor_id, period)


@router.get("/flavors/{flavor_id}/usage-history", response_model=FlavorUsageHistory)
async def get_flavor_usage_history(
    flavor_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated usage history for a flavor.

    - **flavor_id**: UUID of the flavor
    - **limit**: Max records to return (1-1000, default 100)
    - **offset**: Pagination offset (default 0)
    - **start_date**: Optional start date filter (ISO datetime)
    - **end_date**: Optional end date filter (ISO datetime)
    """
    return await FlavorAnalyticsService.get_usage_history(
        db, flavor_id, limit, offset, start_date, end_date
    )


@router.post("/flavors/validate-prompt", response_model=PromptValidationResponse)
async def validate_prompt(
    request: PromptValidationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Pre-flight validation: check if prompt placeholder count matches processing mode.

    Used by frontend to validate prompts before creating/updating flavors.

    - **processing_mode**: Target processing mode (single_pass, iterative, map_reduce)
    - **prompt_content**: Inline prompt content to validate
    - **user_prompt_template_id**: Or template ID to fetch and validate

    Either prompt_content or user_prompt_template_id must be provided.
    """
    content = request.prompt_content

    # If template ID provided, fetch content
    if not content and request.user_prompt_template_id:
        from app.models.prompt import Prompt
        result = await db.execute(
            select(Prompt).where(Prompt.id == request.user_prompt_template_id)
        )
        template = result.scalar_one_or_none()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt template not found"
            )
        content = template.content

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide prompt_content or user_prompt_template_id"
        )

    actual = count_placeholders(content)
    required = get_required_placeholders(request.processing_mode)
    is_valid = actual == required

    return PromptValidationResponse(
        valid=is_valid,
        placeholder_count=actual,
        processing_mode=request.processing_mode,
        required_placeholders=required,
        error=None if is_valid else f"Expected {required} placeholder(s), found {actual}"
    )
