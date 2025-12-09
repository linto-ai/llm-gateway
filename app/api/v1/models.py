#!/usr/bin/env python3
import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.services.model_service import model_service
from app.schemas.model import (
    ModelCreate,
    ModelUpdate,
    ModelResponse,
    ModelVerificationResponse,
    ProviderModelsVerificationResponse,
    ModelLimitsResponse,
)
from app.schemas.common import ErrorResponse, PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["models"])


@router.post(
    "/providers/{provider_id}/models",
    response_model=ModelResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    }
)
async def create_model(
    provider_id: UUID,
    request: ModelCreate,
    db: AsyncSession = Depends(get_db)
) -> ModelResponse:
    """
    Create a new model for a provider.

    - **provider_id**: Provider UUID
    - **model_name**: Human-readable model name
    - **model_identifier**: API identifier used in requests
    - **context_length**: Total context window in tokens
    - **max_generation_length**: Maximum generation tokens
    - **tokenizer_class**: Optional tokenizer class name
    - **tokenizer_name**: Optional HuggingFace tokenizer identifier
    - **is_active**: Whether model is available (default: true)
    - **metadata**: Optional additional configuration
    """
    try:
        return await model_service.create_model(db, provider_id, request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating model: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create model: {str(e)}"
        )


@router.get(
    "/providers/{provider_id}/models",
    response_model=PaginatedResponse[ModelResponse],
    responses={
        404: {"model": ErrorResponse},
    }
)
async def list_models(
    provider_id: UUID,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[ModelResponse]:
    """
    List all models for a provider with optional filtering.

    - **provider_id**: Provider UUID
    - **is_active**: Filter by active status
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 50, max: 100)
    """
    try:
        skip = (page - 1) * page_size
        result = await model_service.get_models_by_provider(
            db=db,
            provider_id=provider_id,
            is_active=is_active,
            skip=skip,
            limit=page_size
        )
        # model_service.get_models_by_provider returns ModelListResponse with items and total
        return PaginatedResponse.create(
            items=result.items,
            total=result.total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}"
        )


@router.get(
    "/models/{model_id}",
    response_model=ModelResponse,
    responses={
        404: {"model": ErrorResponse},
    }
)
async def get_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> ModelResponse:
    """
    Get details for a specific model.

    - **model_id**: Model UUID
    """
    result = await model_service.get_model_by_id(db, model_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    return result


@router.get(
    "/models/{model_id}/limits",
    response_model=ModelLimitsResponse,
    responses={
        404: {"model": ErrorResponse},
    }
)
async def get_model_limits(
    model_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> ModelLimitsResponse:
    """
    Get effective model limits with source information.

    Returns the effective context and generation limits, taking into account
    any manual overrides, with source tracking.

    - **model_id**: Model UUID

    **Response fields:**
    - `context_length`: Effective context length (override > known > discovered > estimated)
    - `max_generation_length`: Effective max generation length
    - `available_for_input`: `context_length - max_generation_length`
    - `limits_source`: One of "documented", "discovered", "manual", "estimated"
    - `has_override`: Boolean indicating if user override is active
    - `discovered_values`: Original values from provider discovery (before overrides/known database)
    """
    return await model_service.get_model_limits(db, model_id)


@router.put(
    "/models/{model_id}",
    response_model=ModelResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    }
)
async def update_model(
    model_id: UUID,
    request: ModelUpdate,
    db: AsyncSession = Depends(get_db)
) -> ModelResponse:
    """
    Update an existing model (full update).

    - **model_id**: Model UUID
    - All fields are optional for partial updates
    """
    try:
        return await model_service.update_model(db, model_id, request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating model: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update model: {str(e)}"
        )


@router.patch(
    "/models/{model_id}",
    response_model=ModelResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    }
)
async def patch_model(
    model_id: UUID,
    request: ModelUpdate,
    db: AsyncSession = Depends(get_db)
) -> ModelResponse:
    """
    Partially update an existing model (PATCH).

    - **model_id**: Model UUID
    - Only provided fields will be updated

    Supports updating:
    - display_name (model_name)
    - context_length_override
    - max_generation_length_override
    - metadata
    - is_active
    """
    try:
        return await model_service.update_model(db, model_id, request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error patching model: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update model: {str(e)}"
        )


@router.delete(
    "/models/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    }
)
async def delete_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete a model.

    - **model_id**: Model UUID

    Note: Cannot delete model if it is referenced by active service flavors.
    """
    try:
        await model_service.delete_model(db, model_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting model: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete model: {str(e)}"
        )


@router.post(
    "/providers/{provider_id}/models/verify",
    response_model=ProviderModelsVerificationResponse,
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    }
)
async def verify_provider_models(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> ProviderModelsVerificationResponse:
    """
    Verify that all models registered for a provider are available through the provider's API.

    This operation:
    - Calls the provider's API to list available models
    - Compares registered models with API response
    - Updates is_active status for each model
    - Returns verification results

    - **provider_id**: Provider UUID
    """
    try:
        return await model_service.verify_provider_models(db, provider_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying models: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model verification failed: {str(e)}"
        )

@router.get(
    "/models",
    response_model=PaginatedResponse[ModelResponse],
    responses={500: {"model": ErrorResponse}},
)
async def list_all_models(
    provider_id: Optional[UUID] = Query(None, description="Filter by provider"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ModelResponse]:
    """
    List ALL models (across all providers) with optional filtering.
    """
    try:
        skip = (page - 1) * page_size
        result = await model_service.list_all_models(
            db=db,
            provider_id=provider_id,
            is_active=is_active,
            skip=skip,
            limit=page_size,
        )

        return PaginatedResponse.create(
            items=result.items,
            total=result.total,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        logger.error(f"Error listing all models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}",
        )


@router.post(
    "/models",
    response_model=ModelResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def create_model_top_level(
    request: ModelCreate,
    db: AsyncSession = Depends(get_db),
) -> ModelResponse:
    """
    Create a new model (top-level endpoint).

    Request must include provider_id in the ModelCreate schema.
    """
    # ModelCreate schema should already have provider_id
    if not hasattr(request, 'provider_id') or not request.provider_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider_id is required",
        )

    try:
        return await model_service.create_model(db, request.provider_id, request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating model: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create model: {str(e)}",
        )


@router.delete(
    "/models/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def delete_model_top_level(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a model (top-level endpoint).
    """
    try:
        await model_service.delete_model(db, model_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting model: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete model: {str(e)}",
        )


@router.post(
    "/models/{model_id}/verify",
    response_model=ModelVerificationResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    }
)
async def verify_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> ModelVerificationResponse:
    """
    Verify model availability via provider API.
    
    Checks if the model is currently available on the provider's API
    and updates the model's health status accordingly.
    
    - **model_id**: Model UUID to verify
    
    Returns health status, timestamp, and diagnostic details.
    """
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.models.provider import Provider
    from app.schemas.model import ModelVerificationResponse as MVR

    # Get model
    model_response = await model_service.get_model_by_id(db, model_id)
    if not model_response:
        raise HTTPException(
            status_code=404,
            detail="Model not found"
        )

    # Get provider (need SQLAlchemy model, not ProviderResponse, to access encrypted credentials)
    result = await db.execute(
        select(Provider).where(Provider.id == model_response.provider_id)
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Provider not found"
        )
    
    # Verify model on provider
    try:
        result = await model_service.verify_model_on_provider(
            provider,
            model_response.model_identifier
        )
        
        # Update health status
        status_value = 'available' if result['available'] else 'unavailable'
        await model_service.update_health_status(
            db,
            model_id,
            status=status_value,
            error=result.get('error')
        )
        
        return MVR(
            model_id=model_id,
            health_status=status_value,
            checked_at=datetime.now(timezone.utc),
            error=result.get('error'),
            details=result.get('details', {})
        )
    
    except Exception as e:
        # Set error status
        await model_service.update_health_status(
            db,
            model_id,
            status='error',
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Verification failed: {str(e)}"
        )
