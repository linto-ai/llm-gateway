#!/usr/bin/env python3
import logging
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_provider_service
from app.services.provider_service import ProviderService
from app.schemas.provider import (
    CreateProviderRequest,
    UpdateProviderRequest,
    ProviderResponse,
)
from app.schemas.model import DiscoveredModel
from app.schemas.common import ErrorResponse, PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/providers", tags=["providers"])


@router.post(
    "",
    response_model=ProviderResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    }
)
async def create_provider(
    request: CreateProviderRequest,
    db: AsyncSession = Depends(get_db),
    service: ProviderService = Depends(get_provider_service)
) -> ProviderResponse:
    """
    Create a new provider with encrypted API key.

    - **name**: Provider name (unique)
    - **provider_type**: Type of provider (openai, anthropic, cohere, custom)
    - **api_base_url**: Base URL for the provider API
    - **api_key**: API key (will be encrypted)
    - **security_level**: Security level (0=Insecure, 1=Medium, 2=Secure)
    - **metadata**: Optional additional configuration
    """
    try:
        return await service.create_provider(db, request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "CREATE_FAILED",
                    "message": "Failed to create provider",
                    "details": str(e)
                }
            }
        )


@router.get(
    "",
    response_model=PaginatedResponse[ProviderResponse],
    responses={
        401: {"model": ErrorResponse},
    }
)
async def list_providers(
    security_level: Optional[int] = Query(None, ge=0, le=2, description="Filter by security level (0, 1, or 2)"),
    provider_type: Optional[str] = Query(None, description="Filter by provider type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    service: ProviderService = Depends(get_provider_service)
) -> PaginatedResponse[ProviderResponse]:
    """
    List providers with optional filtering and pagination.

    - **security_level**: Filter by security level (0=Insecure, 1=Medium, 2=Secure)
    - **provider_type**: Filter by provider type
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    """
    try:
        providers, total = await service.list_providers(
            db=db,
            security_level=security_level,
            provider_type=provider_type,
            page=page,
            limit=page_size
        )
        return PaginatedResponse.create(
            items=providers,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Error listing providers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "LIST_FAILED",
                    "message": "Failed to list providers",
                    "details": str(e)
                }
            }
        )


@router.get(
    "/{provider_id}",
    response_model=ProviderResponse,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    }
)
async def get_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    service: ProviderService = Depends(get_provider_service)
) -> ProviderResponse:
    """
    Get a provider by ID.

    - **provider_id**: UUID of the provider
    """
    try:
        prov_id = UUID(provider_id)

        provider = await service.get_provider(db, prov_id)

        if provider is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "PROVIDER_NOT_FOUND",
                        "message": "Provider not found or access forbidden"
                    }
                }
            )

        return provider
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_UUID",
                    "message": "Invalid UUID format",
                    "details": str(e)
                }
            }
        )
    except Exception as e:
        logger.error(f"Error getting provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "GET_FAILED",
                    "message": "Failed to get provider",
                    "details": str(e)
                }
            }
        )


@router.patch(
    "/{provider_id}",
    response_model=ProviderResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    }
)
async def update_provider(
    provider_id: str,
    request: UpdateProviderRequest,
    db: AsyncSession = Depends(get_db),
    service: ProviderService = Depends(get_provider_service)
) -> ProviderResponse:
    """
    Update a provider.

    - **provider_id**: UUID of the provider to update
    - **name**: Optional new name
    - **api_base_url**: Optional new API base URL
    - **api_key**: Optional new API key (will be re-encrypted)
    - **security_level**: Optional new security level
    - **metadata**: Optional new metadata
    """
    try:
        prov_id = UUID(provider_id)

        provider = await service.update_provider(db, prov_id, request)

        if provider is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "PROVIDER_NOT_FOUND",
                        "message": "Provider not found or access forbidden"
                    }
                }
            )

        return provider
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_UUID",
                    "message": "Invalid UUID format",
                    "details": str(e)
                }
            }
        )
    except Exception as e:
        logger.error(f"Error updating provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "UPDATE_FAILED",
                    "message": "Failed to update provider",
                    "details": str(e)
                }
            }
        )


@router.delete(
    "/{provider_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    }
)
async def delete_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    service: ProviderService = Depends(get_provider_service)
) -> None:
    """
    Delete a provider.

    - **provider_id**: UUID of the provider to delete
    """
    try:
        prov_id = UUID(provider_id)

        deleted = await service.delete_provider(db, prov_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "PROVIDER_NOT_FOUND",
                        "message": "Provider not found or access forbidden"
                    }
                }
            )

        return None
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_UUID",
                    "message": "Invalid UUID format",
                    "details": str(e)
                }
            }
        )
    except Exception as e:
        logger.error(f"Error deleting provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "DELETE_FAILED",
                    "message": "Failed to delete provider",
                    "details": str(e)
                }
            }
        )


@router.get(
    "/{provider_id}/discover-models",
    response_model=List[DiscoveredModel],
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    }
)
async def discover_models(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    service: ProviderService = Depends(get_provider_service)
) -> List[DiscoveredModel]:
    """
    Discover available models from provider API.

    Queries the provider's API to retrieve a list of all available models
    with their specifications.

    - **provider_id**: Provider UUID

    Returns list of discovered models with metadata.
    """
    from sqlalchemy import select
    from app.models.provider import Provider
    from app.services.model_service import model_service

    # Get provider (need SQLAlchemy model, not ProviderResponse, to access encrypted credentials)
    result = await db.execute(
        select(Provider).where(Provider.id == provider_id)
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Provider not found"
        )

    try:
        models = await model_service.discover_models_from_provider(provider)
        return [DiscoveredModel(**model) for model in models]

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Discovery failed for provider {provider_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Discovery failed: {str(e)}"
        )
