#!/usr/bin/env python3
import logging
from typing import Optional, Tuple, List
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.models.provider import Provider
from app.schemas.provider import CreateProviderRequest, UpdateProviderRequest, ProviderResponse
from app.core.security import get_encryption_service
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class ProviderService:
    """Service layer for provider business logic."""

    def __init__(self):
        self.encryption_service = get_encryption_service()

    def _to_response(self, provider: Provider) -> ProviderResponse:
        """Convert Provider model to response schema."""
        return ProviderResponse(
            id=str(provider.id),
            name=provider.name,
            provider_type=provider.provider_type,
            api_base_url=provider.api_base_url,
            api_key_exists=bool(provider.api_key_encrypted),
            security_level=provider.security_level,
            created_at=provider.created_at,
            updated_at=provider.updated_at,
            metadata=provider.provider_metadata or {}
        )

    async def create_provider(
        self,
        db: AsyncSession,
        request: CreateProviderRequest
    ) -> ProviderResponse:
        """
        Create a new provider with encrypted API key.

        Args:
            db: Database session
            request: Provider creation request

        Returns:
            Created provider response

        Raises:
            HTTPException: 409 if provider name already exists
        """
        # Encrypt API key
        encrypted_key = self.encryption_service.encrypt(request.api_key)

        # Create provider
        provider = Provider(
            name=request.name,
            provider_type=request.provider_type,
            api_base_url=request.api_base_url,
            api_key_encrypted=encrypted_key,
            security_level=request.security_level,
            provider_metadata=request.metadata or {}
        )

        db.add(provider)

        try:
            await db.flush()
            await db.refresh(provider)
        except IntegrityError as e:
            await db.rollback()
            if "uq_provider_name" in str(e):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": {
                            "code": "DUPLICATE_PROVIDER",
                            "message": f"Provider with name '{request.name}' already exists"
                        }
                    }
                )
            raise

        logger.info(f"Created provider: {provider.id} ({provider.name})")
        return self._to_response(provider)

    async def get_provider(
        self,
        db: AsyncSession,
        provider_id: UUID
    ) -> Optional[ProviderResponse]:
        """
        Get provider by ID.

        Args:
            db: Database session
            provider_id: Provider UUID

        Returns:
            Provider response or None if not found
        """
        query = select(Provider).where(Provider.id == provider_id)

        result = await db.execute(query)
        provider = result.scalar_one_or_none()

        if provider is None:
            return None

        return self._to_response(provider)

    async def list_providers(
        self,
        db: AsyncSession,
        security_level: Optional[str] = None,
        provider_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[List[ProviderResponse], int]:
        """
        List providers with filtering and pagination.

        Args:
            db: Database session
            security_level: Optional security level filter
            provider_type: Optional provider type filter
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Tuple of (provider list, total count)
        """
        query = select(Provider)

        # Apply filters
        if security_level:
            query = query.where(Provider.security_level == security_level)
        if provider_type:
            query = query.where(Provider.provider_type == provider_type)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.offset((page - 1) * limit).limit(limit)
        query = query.order_by(Provider.created_at.desc())

        # Execute query
        result = await db.execute(query)
        providers = result.scalars().all()

        return [self._to_response(p) for p in providers], total

    async def update_provider(
        self,
        db: AsyncSession,
        provider_id: UUID,
        request: UpdateProviderRequest
    ) -> Optional[ProviderResponse]:
        """
        Update provider.

        Args:
            db: Database session
            provider_id: Provider UUID
            request: Update request

        Returns:
            Updated provider response or None if not found

        Raises:
            HTTPException: 409 if name conflict occurs
        """
        # Fetch provider
        query = select(Provider).where(Provider.id == provider_id)

        result = await db.execute(query)
        provider = result.scalar_one_or_none()

        if provider is None:
            return None

        # Update fields
        if request.name is not None:
            provider.name = request.name
        if request.api_base_url is not None:
            provider.api_base_url = request.api_base_url
        if request.api_key is not None:
            provider.api_key_encrypted = self.encryption_service.encrypt(request.api_key)
        if request.security_level is not None:
            provider.security_level = request.security_level
        if request.metadata is not None:
            provider.provider_metadata = request.metadata

        try:
            await db.flush()
            await db.refresh(provider)
        except IntegrityError as e:
            await db.rollback()
            if "uq_provider_name" in str(e):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": {
                            "code": "DUPLICATE_PROVIDER",
                            "message": f"Provider with name '{request.name}' already exists"
                        }
                    }
                )
            raise

        logger.info(f"Updated provider: {provider.id} ({provider.name})")
        return self._to_response(provider)

    async def delete_provider(
        self,
        db: AsyncSession,
        provider_id: UUID
    ) -> bool:
        """
        Delete provider.

        Args:
            db: Database session
            provider_id: Provider UUID

        Returns:
            True if deleted, False if not found
        """
        # Fetch provider
        query = select(Provider).where(Provider.id == provider_id)

        result = await db.execute(query)
        provider = result.scalar_one_or_none()

        if provider is None:
            return False

        await db.delete(provider)
        await db.flush()

        logger.info(f"Deleted provider: {provider_id}")
        return True

    async def get_decrypted_api_key(
        self,
        db: AsyncSession,
        provider_id: UUID
    ) -> Optional[str]:
        """
        Get decrypted API key for internal use only.

        Args:
            db: Database session
            provider_id: Provider UUID

        Returns:
            Decrypted API key or None if provider not found
        """
        result = await db.execute(
            select(Provider.api_key_encrypted).where(Provider.id == provider_id)
        )
        encrypted_key = result.scalar_one_or_none()

        if encrypted_key is None:
            return None

        return self.encryption_service.decrypt(encrypted_key)


# Global service instance
provider_service = ProviderService()
