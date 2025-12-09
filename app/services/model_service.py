#!/usr/bin/env python3
import asyncio
import logging
import aiohttp
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.models.model import Model
from app.models.provider import Provider
from app.schemas.model import (
    ModelCreate, ModelUpdate, ModelResponse, ModelListResponse,
    ModelVerificationResult, ProviderModelsVerificationResponse,
    ModelLimitsResponse
)
from app.core.security import get_encryption_service
from app.core.model_limits import match_model_limits, get_conservative_estimate
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class ModelService:
    """Service layer for model business logic."""

    def __init__(self):
        self.encryption_service = get_encryption_service()

    def _to_response(self, model: Model) -> ModelResponse:
        """Convert Model ORM object to response schema (includes health fields)."""
        return ModelResponse(
            id=model.id,
            provider_id=model.provider_id,
            model_name=model.model_name,
            model_identifier=model.model_identifier,
            context_length=model.context_length,
            max_generation_length=model.max_generation_length,
            tokenizer_class=model.tokenizer_class,
            tokenizer_name=model.tokenizer_name,
            is_active=model.is_active,
            health_status=getattr(model, 'health_status', 'unknown'),
            health_checked_at=getattr(model, 'health_checked_at', None),
            health_error=getattr(model, 'health_error', None),
            metadata=model.model_metadata or {},
            # Extended fields
            huggingface_repo=getattr(model, 'huggingface_repo', None),
            security_level=getattr(model, 'security_level', None),
            deployment_name=getattr(model, 'deployment_name', None),
            description=getattr(model, 'description', None),
            best_use=getattr(model, 'best_use', None),
            usage_type=getattr(model, 'usage_type', None),
            system_prompt=getattr(model, 'system_prompt', None),
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    async def create_model(
        self,
        db: AsyncSession,
        provider_id: UUID,
        request: ModelCreate
    ) -> ModelResponse:
        """
        Create a new model for a provider.

        Args:
            db: Database session
            provider_id: Provider UUID
            request: Model creation request

        Returns:
            Created model response

        Raises:
            HTTPException: 404 if provider not found
            HTTPException: 409 if model identifier already exists for provider
        """
        # Verify provider exists
        provider_result = await db.execute(
            select(Provider).where(Provider.id == provider_id)
        )
        provider = provider_result.scalar_one_or_none()

        if not provider:
            raise HTTPException(
                status_code=404,
                detail="Provider not found"
            )

        # Create model
        model = Model(
            provider_id=provider_id,
            model_name=request.model_name,
            model_identifier=request.model_identifier,
            context_length=request.context_length,
            max_generation_length=request.max_generation_length,
            tokenizer_class=request.tokenizer_class,
            tokenizer_name=request.tokenizer_name,
            is_active=request.is_active,
            model_metadata=request.metadata or {},
            # Extended fields
            huggingface_repo=getattr(request, 'huggingface_repo', None),
            security_level=getattr(request, 'security_level', None),
            deployment_name=getattr(request, 'deployment_name', None),
            description=getattr(request, 'description', None),
            best_use=getattr(request, 'best_use', None),
            usage_type=getattr(request, 'usage_type', None),
            system_prompt=getattr(request, 'system_prompt', None),
        )

        db.add(model)

        try:
            await db.flush()
            await db.refresh(model)
        except IntegrityError as e:
            await db.rollback()
            if "uq_provider_model_identifier" in str(e):
                raise HTTPException(
                    status_code=409,
                    detail=f"Model with identifier '{request.model_identifier}' already exists for this provider"
                )
            raise

        logger.info(f"Created model: {model.id} ({model.model_name})")

        # Preload tokenizer in background (non-blocking)
        self._preload_tokenizer_async(model)

        return self._to_response(model)

    async def get_models_by_provider(
        self,
        db: AsyncSession,
        provider_id: UUID,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> ModelListResponse:
        """
        Get all models for a provider with optional filtering.

        Args:
            db: Database session
            provider_id: Provider UUID
            is_active: Filter by active status
            skip: Pagination offset
            limit: Page size

        Returns:
            List of models with total count
        """
        # Build query
        query = select(Model).where(Model.provider_id == provider_id)

        if is_active is not None:
            query = query.where(Model.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(Model.created_at.desc())
        result = await db.execute(query)
        models = result.scalars().all()

        return ModelListResponse(
            total=total,
            items=[self._to_response(m) for m in models]
        )

    async def get_model_by_id(
        self,
        db: AsyncSession,
        model_id: UUID
    ) -> Optional[ModelResponse]:
        """
        Get a single model by ID.

        Args:
            db: Database session
            model_id: Model UUID

        Returns:
            Model response or None if not found
        """
        result = await db.execute(
            select(Model).where(Model.id == model_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._to_response(model)

    async def update_model(
        self,
        db: AsyncSession,
        model_id: UUID,
        request: ModelUpdate
    ) -> ModelResponse:
        """
        Update an existing model.

        Args:
            db: Database session
            model_id: Model UUID
            request: Model update request

        Returns:
            Updated model response

        Raises:
            HTTPException: 404 if model not found
        """
        result = await db.execute(
            select(Model).where(Model.id == model_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            raise HTTPException(
                status_code=404,
                detail="Model not found"
            )

        # Update fields if provided
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(model, field, value)

        try:
            await db.flush()
            await db.refresh(model)
        except IntegrityError as e:
            await db.rollback()
            if "uq_provider_model_identifier" in str(e):
                raise HTTPException(
                    status_code=409,
                    detail="Model identifier already exists for this provider"
                )
            raise

        logger.info(f"Updated model: {model.id}")
        return self._to_response(model)

    async def delete_model(
        self,
        db: AsyncSession,
        model_id: UUID
    ) -> None:
        """
        Delete a model.

        Args:
            db: Database session
            model_id: Model UUID

        Raises:
            HTTPException: 404 if model not found
            HTTPException: 409 if model is referenced by service flavors
        """
        from app.models.service_flavor import ServiceFlavor
        
        result = await db.execute(
            select(Model).where(Model.id == model_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            raise HTTPException(
                status_code=404,
                detail="Model not found"
            )

        # Check if model is referenced by any service flavors
        flavor_check = await db.execute(
            select(ServiceFlavor).where(ServiceFlavor.model_id == model_id).limit(1)
        )
        if flavor_check.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail="Model is referenced by service flavors"
            )

        await db.delete(model)
        await db.flush()
        logger.info(f"Deleted model: {model_id}")

    async def verify_provider_models(
        self,
        db: AsyncSession,
        provider_id: UUID,
        timeout: int = 10
    ) -> ProviderModelsVerificationResponse:
        """
        Verify all models for a provider by calling the provider's API.

        Args:
            db: Database session
            provider_id: Provider UUID
            timeout: API request timeout in seconds

        Returns:
            Verification response with results for each model

        Raises:
            HTTPException: 404 if provider not found
            HTTPException: 503 if provider API is unreachable
        """
        # Fetch provider with decrypted API key
        result = await db.execute(
            select(Provider).where(Provider.id == provider_id)
        )
        provider = result.scalar_one_or_none()

        if not provider:
            raise HTTPException(
                status_code=404,
                detail="Provider not found"
            )

        # Decrypt API key
        try:
            api_key = self.encryption_service.decrypt(provider.api_key_encrypted)
        except Exception as e:
            logger.error(f"Failed to decrypt API key for provider {provider_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to decrypt provider credentials"
            )

        # Fetch all models for this provider
        models_result = await db.execute(
            select(Model).where(Model.provider_id == provider_id)
        )
        models = models_result.scalars().all()

        if not models:
            return ProviderModelsVerificationResponse(
                provider_id=provider_id,
                total_models=0,
                verified_count=0,
                failed_count=0,
                results=[],
                verified_at=datetime.utcnow()
            )

        # Call provider API to list available models
        available_model_ids = set()
        try:
            available_model_ids = await self._fetch_available_models(
                provider.api_base_url,
                api_key,
                timeout
            )
        except Exception as e:
            logger.error(f"Failed to fetch models from provider API: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Provider API unreachable: {str(e)}"
            )

        # Verify each model
        results = []
        verified_count = 0
        failed_count = 0

        for model in models:
            if model.model_identifier in available_model_ids:
                # Model is available
                model.is_active = True
                model.health_status = "available"
                model.health_checked_at = datetime.utcnow()
                model.health_error = None
                results.append(
                    ModelVerificationResult(
                        model_id=model.id,
                        model_identifier=model.model_identifier,
                        status="available",
                        error_message=None
                    )
                )
                verified_count += 1
            else:
                # Model not found in provider API
                model.is_active = False
                model.health_status = "unavailable"
                model.health_checked_at = datetime.utcnow()
                model.health_error = "Model not found in provider API response"
                results.append(
                    ModelVerificationResult(
                        model_id=model.id,
                        model_identifier=model.model_identifier,
                        status="unavailable",
                        error_message="Model not found in provider API response"
                    )
                )
                failed_count += 1

        # Commit changes
        await db.flush()

        logger.info(
            f"Verified {verified_count}/{len(models)} models for provider {provider_id}"
        )

        return ProviderModelsVerificationResponse(
            provider_id=provider_id,
            total_models=len(models),
            verified_count=verified_count,
            failed_count=failed_count,
            results=results,
            verified_at=datetime.utcnow()
        )

    async def _fetch_available_models(
        self,
        api_base_url: str,
        api_key: str,
        timeout: int
    ) -> set[str]:
        """
        Fetch available models from provider API.

        Args:
            api_base_url: Provider API base URL
            api_key: Decrypted API key
            timeout: Request timeout

        Returns:
            Set of available model identifiers

        Raises:
            Exception: If API request fails
        """
        # Normalize base URL (remove trailing slash)
        base_url = api_base_url.rstrip('/')

        # Build models endpoint URL (OpenAI-compatible)
        models_url = f"{base_url}/models"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                models_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"Provider API returned status {response.status}: {error_text}"
                    )

                data = await response.json()

                # Parse response (OpenAI-compatible format)
                # Expected format: {"data": [{"id": "model-id", ...}, ...]}
                if "data" not in data:
                    raise Exception("Invalid API response format: missing 'data' field")

                model_ids = {model["id"] for model in data["data"] if "id" in model}
                return model_ids


    async def list_all_models(
        self,
        db: AsyncSession,
        provider_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> ModelListResponse:
        """List all models across all providers with optional filtering."
        """
        from sqlalchemy.orm import joinedload

        stmt = select(Model).options(joinedload(Model.provider))

        if provider_id:
            stmt = stmt.where(Model.provider_id == provider_id)
        if is_active is not None:
            stmt = stmt.where(Model.is_active == is_active)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await db.scalar(count_stmt) or 0

        # Apply pagination
        stmt = stmt.order_by(Model.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        models = result.unique().scalars().all()

        # Convert to response
        items = [
            ModelResponse(
                id=model.id,
                model_name=model.model_name,
                model_identifier=model.model_identifier,
                provider_id=model.provider_id,
                provider_name=model.provider.name,
                context_length=model.context_length,
                max_generation_length=model.max_generation_length,
                tokenizer_class=model.tokenizer_class,
                tokenizer_name=model.tokenizer_name,
                is_active=model.is_active,
                health_status=getattr(model, 'health_status', 'unknown'),
                health_checked_at=getattr(model, 'health_checked_at', None),
                health_error=getattr(model, 'health_error', None),
                metadata=model.model_metadata or {},
                # Extended fields
                huggingface_repo=getattr(model, 'huggingface_repo', None),
                security_level=getattr(model, 'security_level', None),
                deployment_name=getattr(model, 'deployment_name', None),
                description=getattr(model, 'description', None),
                best_use=getattr(model, 'best_use', None),
                usage_type=getattr(model, 'usage_type', None),
                system_prompt=getattr(model, 'system_prompt', None),
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for model in models
        ]

        return ModelListResponse(items=items, total=total)





    async def update_health_status(
        self,
        db: AsyncSession,
        model_id: UUID,
        status: str,
        error: Optional[str] = None
    ) -> ModelResponse:
        """
        Update model health status.
        
        Args:
            db: Database session
            model_id: Model UUID
            status: Health status ('available', 'unavailable', 'unknown', 'error')
            error: Optional error message
            
        Returns:
            Updated model response
            
        Raises:
            HTTPException: 404 if model not found
        """
        from datetime import timezone
        
        result = await db.execute(
            select(Model).where(Model.id == model_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            raise HTTPException(
                status_code=404,
                detail="Model not found"
            )
        
        model.health_status = status
        model.health_checked_at = datetime.now(timezone.utc)
        model.health_error = error
        
        await db.flush()
        await db.refresh(model)
        
        logger.info(f"Updated health status for model {model_id}: {status}")
        return self._to_response(model)
    
    async def verify_model_on_provider(
        self,
        provider: Provider,
        model_identifier: str,
        timeout: int = 10
    ) -> dict:
        """
        Verify model availability via provider API.
        
        Args:
            provider: Provider object with credentials
            model_identifier: Model identifier to verify
            timeout: Request timeout in seconds
            
        Returns:
            Dict with verification result:
            - available: bool
            - error: Optional[str]
            - details: dict
        """
        # Decrypt API key
        try:
            api_key = self.encryption_service.decrypt(provider.api_key_encrypted)
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}")
            return {
                "available": False,
                "error": "Failed to decrypt provider credentials",
                "details": {}
            }
        
        # Route to appropriate verification method based on provider type
        if provider.provider_type == 'openai':
            return await self._verify_openai_model(provider, model_identifier, api_key, timeout)
        elif provider.provider_type == 'anthropic':
            return await self._verify_anthropic_model(provider, model_identifier, api_key, timeout)
        elif provider.provider_type == 'openrouter':
            return await self._verify_openrouter_model(provider, model_identifier, api_key, timeout)
        else:
            # Custom provider: Attempt OpenAI-compatible verification
            return await self._verify_custom_model(provider, model_identifier, api_key, timeout)
    
    async def _verify_openai_model(
        self,
        provider: Provider,
        model_identifier: str,
        api_key: str,
        timeout: int
    ) -> dict:
        """Verify OpenAI model via /v1/models endpoint.

        First tries to fetch individual model via /v1/models/{id}.
        If that returns 404, falls back to listing all models and checking if model exists.
        """
        import time

        base_url = (provider.api_base_url or "https://api.openai.com/v1").rstrip('/')

        try:
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                # Try individual model endpoint first
                async with session.get(
                    f"{base_url}/models/{model_identifier}",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    latency_ms = int((time.time() - start_time) * 1000)

                    if response.status == 200:
                        data = await response.json()
                        return {
                            "available": True,
                            "error": None,
                            "details": {
                                "latency_ms": latency_ms,
                                "provider_response": data
                            }
                        }
                    elif response.status == 404:
                        # Individual model endpoint not supported, try list endpoint
                        logger.info(f"Individual model endpoint not found, trying list endpoint for {model_identifier}")

                        async with session.get(
                            f"{base_url}/models",
                            headers={"Authorization": f"Bearer {api_key}"},
                            timeout=aiohttp.ClientTimeout(total=timeout)
                        ) as list_response:
                            latency_ms = int((time.time() - start_time) * 1000)

                            if list_response.status == 200:
                                data = await list_response.json()
                                model_ids = {model["id"] for model in data.get("data", []) if "id" in model}

                                logger.info(f"OpenAI verification fallback: looking for '{model_identifier}' in {len(model_ids)} models")

                                if model_identifier in model_ids:
                                    return {
                                        "available": True,
                                        "error": None,
                                        "details": {"latency_ms": latency_ms}
                                    }
                                else:
                                    return {
                                        "available": False,
                                        "error": f"Model '{model_identifier}' not found on provider",
                                        "details": {"latency_ms": latency_ms}
                                    }
                            else:
                                error_text = await list_response.text()
                                return {
                                    "available": False,
                                    "error": f"Models list API returned {list_response.status}: {error_text[:200]}",
                                    "details": {"latency_ms": latency_ms}
                                }
                    else:
                        error_text = await response.text()
                        return {
                            "available": False,
                            "error": f"API returned {response.status}: {error_text[:200]}",
                            "details": {"latency_ms": latency_ms}
                        }
        except aiohttp.ClientError as e:
            return {
                "available": False,
                "error": f"Provider API timeout or connection error: {str(e)}",
                "details": {}
            }
        except Exception as e:
            return {
                "available": False,
                "error": f"Verification failed: {str(e)}",
                "details": {}
            }
    
    async def _verify_anthropic_model(
        self,
        provider: Provider,
        model_identifier: str,
        api_key: str,
        timeout: int
    ) -> dict:
        """Verify Anthropic model (simplified - assumes available if API key works)."""
        # Anthropic doesn't have a models list endpoint, so we do a minimal check
        (provider.api_base_url or "https://api.anthropic.com").rstrip('/')
        
        try:
            # Known Anthropic model patterns
            known_models = [
                'claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku',
                'claude-2.1', 'claude-2.0', 'claude-instant'
            ]
            
            is_known = any(pattern in model_identifier for pattern in known_models)
            
            if is_known:
                return {
                    "available": True,
                    "error": None,
                    "details": {"verification_method": "pattern_matching"}
                }
            else:
                return {
                    "available": False,
                    "error": f"Unknown Anthropic model: {model_identifier}",
                    "details": {}
                }
        except Exception as e:
            return {
                "available": False,
                "error": f"Verification failed: {str(e)}",
                "details": {}
            }
    
    async def _verify_openrouter_model(
        self,
        provider: Provider,
        model_identifier: str,
        api_key: str,
        timeout: int
    ) -> dict:
        """Verify OpenRouter model via /api/v1/models endpoint."""
        base_url = (provider.api_base_url or "https://openrouter.ai/api").rstrip('/')
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{base_url}/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("data", [])
                        model_ids = {m["id"] for m in models if "id" in m}
                        
                        if model_identifier in model_ids:
                            return {
                                "available": True,
                                "error": None,
                                "details": {"total_models_available": len(model_ids)}
                            }
                        else:
                            return {
                                "available": False,
                                "error": f"Model '{model_identifier}' not found in OpenRouter catalog",
                                "details": {}
                            }
                    else:
                        error_text = await response.text()
                        return {
                            "available": False,
                            "error": f"API returned {response.status}: {error_text[:200]}",
                            "details": {}
                        }
        except Exception as e:
            return {
                "available": False,
                "error": f"Verification failed: {str(e)}",
                "details": {}
            }
    
    async def _verify_custom_model(
        self,
        provider: Provider,
        model_identifier: str,
        api_key: str,
        timeout: int
    ) -> dict:
        """Verify custom provider model by checking models list."""
        import time

        base_url = provider.api_base_url.rstrip('/')

        try:
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    latency_ms = int((time.time() - start_time) * 1000)

                    if response.status == 200:
                        data = await response.json()
                        # Check if model is in the list
                        model_ids = {model["id"] for model in data.get("data", []) if "id" in model}

                        logger.info(f"Custom provider verification: looking for '{model_identifier}' in {len(model_ids)} models")
                        logger.debug(f"Available model IDs: {model_ids}")

                        if model_identifier in model_ids:
                            return {
                                "available": True,
                                "error": None,
                                "details": {"latency_ms": latency_ms}
                            }
                        else:
                            return {
                                "available": False,
                                "error": f"Model '{model_identifier}' not found on provider",
                                "details": {"latency_ms": latency_ms}
                            }
                    else:
                        error_text = await response.text()
                        return {
                            "available": False,
                            "error": f"Provider API returned status {response.status}: {error_text}",
                            "details": {"latency_ms": latency_ms}
                        }
        except asyncio.TimeoutError:
            return {
                "available": False,
                "error": "Request timed out",
                "details": {}
            }
        except Exception as e:
            logger.error(f"Custom model verification error: {e}")
            return {
                "available": False,
                "error": f"Verification failed: {str(e)}",
                "details": {}
            }
    
    async def discover_models_from_provider(
        self,
        provider: Provider,
        timeout: int = 30
    ) -> List[dict]:
        """
        Query provider for available models.
        
        Args:
            provider: Provider object with credentials
            timeout: Request timeout in seconds
            
        Returns:
            List of discovered model dicts
            
        Raises:
            ValueError: If provider type doesn't support discovery
            HTTPException: If API request fails
        """
        # Decrypt API key
        try:
            api_key = self.encryption_service.decrypt(provider.api_key_encrypted)
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to decrypt provider credentials"
            )
        
        # Route to appropriate discovery method
        if provider.provider_type == 'openai':
            return await self._discover_openai_models(provider, api_key, timeout)
        elif provider.provider_type == 'openrouter':
            return await self._discover_openrouter_models(provider, api_key, timeout)
        elif provider.provider_type == 'anthropic':
            # Anthropic doesn't have a discovery endpoint
            return await self._discover_anthropic_models(provider)
        elif provider.provider_type in ('custom', 'vllm', 'ollama', 'openai_compatible'):
            # Attempt OpenAI-compatible discovery for custom providers
            return await self._discover_openai_models(provider, api_key, timeout)
        else:
            raise ValueError(f"Model discovery not supported for provider type: {provider.provider_type}")
    
    async def _discover_openai_models(
        self,
        provider: Provider,
        api_key: str,
        timeout: int
    ) -> List[dict]:
        """Discover OpenAI models via /v1/models endpoint."""
        base_url = (provider.api_base_url or "https://api.openai.com/v1").rstrip('/')
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=500,
                        detail=f"Provider API returned {response.status}: {error_text[:200]}"
                    )
                
                data = await response.json()
                models_data = data.get("data", [])
                
                # Map OpenAI model data to DiscoveredModel format
                discovered = []
                for model in models_data:
                    model_id = model.get("id", "")
                    tokenizer_class, tokenizer_name = self._get_tokenizer_info(model_id)

                    # Extract extended metadata from provider API (GPT@EC format support)
                    discovered_model = self._extract_extended_metadata(model, model_id, tokenizer_class, tokenizer_name)
                    discovered.append(discovered_model)

                return discovered
    
    async def _discover_openrouter_models(
        self,
        provider: Provider,
        api_key: str,
        timeout: int
    ) -> List[dict]:
        """Discover OpenRouter models via /api/v1/models endpoint."""
        base_url = (provider.api_base_url or "https://openrouter.ai/api").rstrip('/')

        # Normalize OpenRouter URL - users may enter various formats
        # Expected format for discovery: https://openrouter.ai/api/v1/models
        if base_url == "https://openrouter.ai":
            base_url = "https://openrouter.ai/api"
        elif base_url.endswith("/v1"):
            # User entered https://openrouter.ai/api/v1 - strip /v1 since we add it below
            base_url = base_url[:-3]
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=500,
                        detail=f"Provider API returned {response.status}: {error_text[:200]}"
                    )
                
                data = await response.json()
                models_data = data.get("data", [])
                
                # Map OpenRouter model data with extended metadata
                discovered = []
                for model in models_data:
                    model_id = model.get("id", "")
                    context_length = model.get("context_length", 4096)

                    # Extract extended metadata
                    discovered_model = self._extract_extended_metadata(model, model_id, None, None)
                    # Override context_length from OpenRouter response
                    discovered_model["context_length"] = context_length
                    discovered_model["max_generation_length"] = min(context_length // 2, 4096)
                    discovered_model["model_name"] = model.get("name", model_id)
                    discovered.append(discovered_model)

                return discovered
    
    async def _discover_anthropic_models(self, provider: Provider) -> List[dict]:
        """Return known Anthropic models (no discovery API available)."""
        # Anthropic doesn't have a models endpoint, return known models
        known_models = [
            {
                "model_identifier": "claude-3-opus-20240229",
                "model_name": "Claude 3 Opus",
                "context_length": 200000,
                "max_generation_length": 4096,
                "tokenizer_class": "anthropic",
                "tokenizer_name": "claude-3",
                "available": True
            },
            {
                "model_identifier": "claude-3-sonnet-20240229",
                "model_name": "Claude 3 Sonnet",
                "context_length": 200000,
                "max_generation_length": 4096,
                "tokenizer_class": "anthropic",
                "tokenizer_name": "claude-3",
                "available": True
            },
            {
                "model_identifier": "claude-3-haiku-20240307",
                "model_name": "Claude 3 Haiku",
                "context_length": 200000,
                "max_generation_length": 4096,
                "tokenizer_class": "anthropic",
                "tokenizer_name": "claude-3",
                "available": True
            }
        ]
        return known_models

    def _extract_extended_metadata(
        self,
        model_data: dict,
        model_id: str,
        tokenizer_class: Optional[str],
        tokenizer_name: Optional[str],
    ) -> dict:
        """
        Extract extended metadata from provider API response.

        Uses known models database for accurate limits. Priority:
        1. Provider API response (discovered)
        2. Known models database (documented)
        3. Conservative estimates (estimated)

        Supports GPT@EC format and standard OpenAI format.
        Fields extracted:
        - description, best_use, sensitivity_level, default_for
        - usage_type, system_prompt, deployment_name, custom_tokenizer

        Args:
            model_data: Raw model data from provider API
            model_id: Model identifier
            tokenizer_class: Tokenizer class (can be overridden by provider data)
            tokenizer_name: Tokenizer name (can be overridden by provider data)

        Returns:
            Dict with DiscoveredModel fields including extended metadata
        """
        # Resolve limits using priority chain
        # 1. Try provider API response
        context_length = model_data.get("context_length")
        max_gen_length = model_data.get("max_generation_length") or model_data.get("max_output_tokens")
        source = "discovered" if context_length and max_gen_length else None

        # 2. Try known models database
        if not context_length or not max_gen_length:
            known = match_model_limits(model_id)
            if known:
                context_length = context_length or known["context_length"]
                max_gen_length = max_gen_length or known["max_generation_length"]
                source = source or known["source"]

        # 3. Fallback to conservative estimates
        if not context_length or not max_gen_length:
            fallback = get_conservative_estimate(model_id)
            context_length = context_length or fallback["context_length"]
            max_gen_length = max_gen_length or fallback["max_generation_length"]
            source = source or fallback["source"]

        # Base fields
        discovered = {
            "model_identifier": model_id,
            "model_name": model_data.get("name", model_id),
            "context_length": context_length,
            "max_generation_length": max_gen_length,
            "tokenizer_class": tokenizer_class,
            "tokenizer_name": tokenizer_name,
            "available": True,
            "limits_source": source,
        }

        # Extended fields from provider API (GPT@EC format)
        discovered["description"] = model_data.get("description")
        discovered["best_use"] = model_data.get("best_use") or model_data.get("bestUse")
        discovered["sensitivity_level"] = model_data.get("sensitivity_level") or model_data.get("sensitivityLevel")
        discovered["default_for"] = model_data.get("default_for") or model_data.get("defaultFor")
        discovered["usage_type"] = model_data.get("usage_type") or model_data.get("usageType")
        discovered["system_prompt"] = model_data.get("system_prompt") or model_data.get("systemPrompt")
        discovered["deployment_name"] = model_data.get("deployment_name") or model_data.get("deploymentName")

        # Custom tokenizer can override inferred tokenizer
        custom_tokenizer = model_data.get("custom_tokenizer") or model_data.get("customTokenizer")
        discovered["custom_tokenizer"] = custom_tokenizer
        if custom_tokenizer:
            discovered["tokenizer_name"] = custom_tokenizer

        # Collect remaining unrecognized fields into metadata
        known_fields = {
            "id", "name", "context_length", "max_generation_length", "max_output_tokens",
            "description", "best_use", "bestUse", "sensitivity_level", "sensitivityLevel",
            "default_for", "defaultFor", "usage_type", "usageType", "system_prompt", "systemPrompt",
            "deployment_name", "deploymentName", "custom_tokenizer", "customTokenizer",
            "object", "created", "owned_by", "permission", "root", "parent"
        }
        extra_metadata = {k: v for k, v in model_data.items() if k not in known_fields}
        discovered["metadata"] = extra_metadata if extra_metadata else None

        return discovered

    def _estimate_context_length(self, model_id: str) -> int:
        """Estimate context length based on model ID."""
        model_id_lower = model_id.lower()
        
        if "gpt-4-turbo" in model_id_lower or "gpt-4-1106" in model_id_lower:
            return 128000
        elif "gpt-4" in model_id_lower:
            return 8192
        elif "gpt-3.5-turbo-16k" in model_id_lower:
            return 16385
        elif "gpt-3.5-turbo" in model_id_lower:
            return 4096
        else:
            return 4096  # Conservative default
    
    def _estimate_max_generation(self, model_id: str) -> int:
        """Estimate max generation length based on model ID."""
        if "gpt-4" in model_id.lower():
            return 4096
        else:
            return 2048
    
    def _get_tokenizer_info(self, model_id: str) -> tuple[str | None, str | None]:
        """Get tokenizer class and name for model based on model ID."""
        model_lower = model_id.lower()

        # OpenAI models use tiktoken
        if "gpt-4" in model_lower or "gpt-3.5" in model_lower:
            return ("tiktoken", "cl100k_base")

        # Mistral models use their own tokenizer
        if "mistral" in model_lower:
            return ("mistral", "mistral-tokenizer")

        # Llama models use sentencepiece-based tokenizer
        if "llama" in model_lower:
            return ("sentencepiece", "llama-tokenizer")

        # Claude models
        if "claude" in model_lower:
            return ("anthropic", "claude-3")

        # Unknown models - return None to indicate unknown tokenizer
        return (None, None)

    def _preload_tokenizer_async(self, model: Model) -> None:
        """
        Preload tokenizer for a model in a non-blocking way.

        Called after model creation and discovery.
        Attempts to preload the tokenizer but does not block on failures.

        Args:
            model: Model ORM object
        """
        try:
            from app.services.tokenizer_manager import TokenizerManager

            manager = TokenizerManager.get_instance()
            result = manager.preload_tokenizer(model)

            if result.success:
                if result.cached:
                    logger.debug(f"Tokenizer already cached for model {model.model_identifier}")
                else:
                    logger.info(f"Preloaded tokenizer for model {model.model_identifier}: {result.tokenizer_id}")
            else:
                logger.warning(f"Failed to preload tokenizer for {model.model_identifier}: {result.message}")
        except Exception as e:
            # Non-blocking: log warning but don't fail the operation
            logger.warning(f"Tokenizer preload failed for {model.model_identifier}: {e}")

    async def get_model_limits(
        self,
        db: AsyncSession,
        model_id: UUID
    ) -> ModelLimitsResponse:
        """
        Get model limits.

        Returns direct model values.

        Args:
            db: Database session
            model_id: Model UUID

        Returns:
            ModelLimitsResponse with model limits

        Raises:
            HTTPException: 404 if model not found
        """
        result = await db.execute(
            select(Model).where(Model.id == model_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        return ModelLimitsResponse(
            model_id=model.id,
            model_name=model.model_name,
            model_identifier=model.model_identifier,
            context_length=model.context_length,
            max_generation_length=model.max_generation_length,
            available_for_input=model.context_length - model.max_generation_length,
        )


model_service = ModelService()

