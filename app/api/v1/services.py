#!/usr/bin/env python3
import logging
import uuid as uuid_module
from typing import Any, Dict, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.dependencies import get_db
from app.services.service_service import service_service
from app.services.document_template_service import document_template_service
from app.core.prompt_validation import count_placeholders
from app.services.tokenizer_manager import TokenizerManager
from app.schemas.service import (
    ServiceCreate,
    ServiceUpdate,
    ServiceResponse,
    ServiceFlavorCreate,
    ServiceFlavorUpdate,
    ServiceFlavorResponse,
    ServiceExecuteRequest,
    ServiceExecuteResponse,
    ExecutionValidationResponse,
    ExecutionErrorResponse,
    FallbackAvailabilityResponse,
    FailoverChainResponse,
    FailoverChainItem,
    ValidateFailoverRequest,
    ValidateFailoverResponse,
)
from app.schemas.common import ErrorResponse, PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["services"])


def resolve_tokenizer_for_flavor(flavor) -> str:
    """
    Resolve the tokenizer to use for a flavor.

    This function uses TokenizerManager to resolve the tokenizer config,
    then returns the appropriate tokenizer identifier string for backward
    compatibility with the existing task_data format.

    Priority (handled by TokenizerManager):
    1. flavor.tokenizer_override (if set)
    2. flavor.model.tokenizer_name (if set)
    3. TOKENIZER_MAPPINGS lookup by model_identifier
    4. Extract base model from quantized identifier
    5. Fallback to tiktoken cl100k_base
    """
    from app.core.tokenizer_mappings import get_tokenizer_config, get_fallback_tokenizer_config

    # Priority 1: flavor.tokenizer_override
    if flavor.tokenizer_override:
        return flavor.tokenizer_override

    # Priority 2: flavor.model.tokenizer_name
    if flavor.model.tokenizer_name:
        return flavor.model.tokenizer_name

    # Use tokenizer mappings for resolution
    config = get_tokenizer_config(flavor.model.model_identifier)
    if not config:
        config = get_fallback_tokenizer_config()

    if config["type"] == "tiktoken":
        # For tiktoken, return the encoding name (will be handled by TokenizerManager)
        return config["encoding"]
    else:
        # For HuggingFace, return the repo
        return config["repo"]


async def _get_extraction_fields(db: AsyncSession, service_id: UUID) -> list[str]:
    """
    Collect custom placeholders from the service's default template for extraction.

    Only returns placeholders that need to be extracted by the LLM.
    STANDARD_PLACEHOLDERS (output, job_date, service_name, etc.) are excluded
    as they are computed at export time.

    No default extraction fields - only template-defined custom placeholders.

    Returns:
        Sorted list of placeholder definitions (with hints if available),
        or empty list if no custom placeholders to extract.
    """
    # Standard placeholders computed at export time - NOT to be extracted by LLM
    standard_placeholders = set(document_template_service.STANDARD_PLACEHOLDERS)

    # No default fields - only extract what the template defines
    extraction_fields = {}

    # Get service's default template (if any)
    service = await service_service.get_service_by_id(db, service_id)
    if service and service.default_template_id:
        template = await document_template_service.get_template(db, service.default_template_id)
        if template and template.placeholders:
            for placeholder in template.placeholders:
                # Extract field name (part before colon, if any)
                # e.g., "cat_count: number of cats" -> "cat_count"
                field_name = placeholder.split(":")[0].strip()
                # Skip STANDARD_PLACEHOLDERS - they're computed at export, not extracted
                if field_name in standard_placeholders:
                    continue
                # Keep the full placeholder with description for LLM guidance
                extraction_fields[field_name] = placeholder

    # Return sorted list of placeholder definitions (empty if no custom placeholders)
    return sorted(list(extraction_fields.values()))


async def _validate_context(
    flavor,
    content: str,
) -> tuple[bool, int, int]:
    """
    Validate if content fits within flavor's context window.

    Uses model's direct limit values.

    Returns:
        tuple: (fits, input_tokens, available_tokens)
    """
    # Count tokens
    try:
        manager = TokenizerManager.get_instance()
        input_tokens = manager.count_tokens(flavor.model, content)
    except Exception as e:
        logger.warning(f"Tokenizer count failed, using estimate: {e}")
        input_tokens = len(content) // 4  # Rough estimate

    # Calculate available tokens using direct model limits
    prompt_buffer = 500  # Reserve for system/user prompts
    context_length = flavor.model.context_length
    max_gen_length = flavor.model.max_generation_length
    available = context_length - max_gen_length - prompt_buffer

    fits = input_tokens <= available
    return fits, input_tokens, available


async def _find_fallback_flavor(
    db,
    service_id: UUID,
    exclude_flavor_id: UUID
):
    """
    Find an iterative fallback flavor for the service.

    Selection criteria:
    1. Same service
    2. is_active=True
    3. processing_mode='iterative'
    4. Exclude current flavor
    5. Order by priority DESC, created_at ASC
    """
    from app.services.flavor_service import FlavorService
    return await FlavorService.find_iterative_fallback(db, service_id, exclude_flavor_id)


@router.post(
    "/services",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    }
)
async def create_service(
    request: ServiceCreate,
    db: AsyncSession = Depends(get_db)
) -> ServiceResponse:
    """
    Create a new service with flavors.

    - **name**: Unique service name (e.g., "summarize-en")
    - **route**: URL route for service endpoint
    - **service_type**: Type of service (summary, translation, categorization, etc.)
    - **description**: i18n descriptions ({"en": "...", "fr": "..."})
    - **organization_id**: Optional organization UUID (null for global services)
    - **is_active**: Whether service is available (default: true)
    - **fields**: Number of expected input fields
    - **flavors**: List of model configurations
    - **metadata**: Optional additional configuration
    """
    try:
        return await service_service.create_service(db, request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating service: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create service: {str(e)}"
        )


@router.get(
    "/services",
    response_model=PaginatedResponse[ServiceResponse],
    responses={
        401: {"model": ErrorResponse},
    }
)
async def list_services(
    service_type: Optional[str] = Query(None, description="Filter by service type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    organization_id: Optional[str] = Query(None, description="Visibility filter - returns global services + org-specific services"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[ServiceResponse]:
    """
    List all services with optional filtering.

    - **service_type**: Filter by service type
    - **is_active**: Filter by active status
    - **organization_id**: Visibility filter - returns global services (no org) plus services matching this org ID
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 50, max: 100)
    """
    try:
        skip = (page - 1) * page_size
        result = await service_service.get_services(
            db=db,
            service_type=service_type,
            is_active=is_active,
            organization_id=organization_id,
            skip=skip,
            limit=page_size
        )
        # service_service.get_services returns ServiceListResponse with items and total
        return PaginatedResponse.create(
            items=result.items,
            total=result.total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Error listing services: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list services: {str(e)}"
        )


@router.get(
    "/services/{service_id}",
    response_model=ServiceResponse,
    responses={
        404: {"model": ErrorResponse},
    }
)
async def get_service(
    service_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> ServiceResponse:
    """
    Get details for a specific service.

    - **service_id**: Service UUID
    """
    result = await service_service.get_service_by_id(db, service_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    return result


@router.patch(
    "/services/{service_id}",
    response_model=ServiceResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    }
)
async def update_service(
    service_id: UUID,
    request: ServiceUpdate,
    db: AsyncSession = Depends(get_db)
) -> ServiceResponse:
    """
    Update an existing service.

    - **service_id**: Service UUID
    - All fields are optional for partial updates
    """
    try:
        return await service_service.update_service(db, service_id, request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating service: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update service: {str(e)}"
        )


@router.delete(
    "/services/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse},
    }
)
async def delete_service(
    service_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete a service (cascades to flavors).

    - **service_id**: Service UUID
    """
    try:
        await service_service.delete_service(db, service_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting service: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete service: {str(e)}"
        )

# Flavor CRUD endpoints

@router.post(
    "/services/{service_id}/flavors",
    response_model=ServiceFlavorResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}}
)
async def add_flavor_to_service(
    service_id: UUID,
    request: ServiceFlavorCreate,
    db: AsyncSession = Depends(get_db)
) -> ServiceFlavorResponse:
    """
    Add a new flavor to an existing service.

    Creates a new service version after successful addition.
    """
    from app.models.service_flavor import ServiceFlavor
    from app.models.prompt import Prompt
    from sqlalchemy import select

    # Verify service exists
    service = await service_service.get_service_by_id(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Map schema field names to model field names
    data = request.model_dump()

    # STEP 1: Handle template ID -> content copying
    # System prompt template
    if 'system_prompt_template_id' in data and data['system_prompt_template_id']:
        template_id = data['system_prompt_template_id']
        result = await db.execute(select(Prompt).where(Prompt.id == template_id))
        template = result.scalar_one_or_none()
        if not template:
            raise HTTPException(status_code=404, detail=f"System prompt template {template_id} not found")
        data['prompt_system_content'] = template.content
        data['system_prompt_id'] = data.pop('system_prompt_template_id')

    # User prompt template - only load from template if inline content not provided
    if 'user_prompt_template_id' in data and data['user_prompt_template_id']:
        template_id = data['user_prompt_template_id']
        # Prioritize inline content if provided (user may have edited the template)
        inline_content = data.get('user_prompt_content') or data.get('prompt_user_content')
        if not inline_content:
            result = await db.execute(select(Prompt).where(Prompt.id == template_id))
            template = result.scalar_one_or_none()
            if not template:
                raise HTTPException(status_code=404, detail=f"User prompt template {template_id} not found")
            data['prompt_user_content'] = template.content
        # user_prompt_template_id stays as-is (model field exists)

    # Reduce prompt template
    if 'reduce_prompt_template_id' in data and data['reduce_prompt_template_id']:
        template_id = data['reduce_prompt_template_id']
        result = await db.execute(select(Prompt).where(Prompt.id == template_id))
        template = result.scalar_one_or_none()
        if not template:
            raise HTTPException(status_code=404, detail=f"Reduce prompt template {template_id} not found")
        data['prompt_reduce_content'] = template.content
        data['reduce_prompt_id'] = data.pop('reduce_prompt_template_id')

    # STEP 2: Remove any leftover *_template_id fields except user_prompt_template_id
    # (system and reduce were already popped above, but handle edge cases)
    for key in list(data.keys()):
        if key.endswith('_template_id') and key != 'user_prompt_template_id':
            data.pop(key, None)

    # Validate prompt compatibility with processing mode
    from app.core.prompt_validation import validate_prompt_for_processing_mode
    processing_mode = data.get('processing_mode', 'iterative')
    prompt_content = data.get('prompt_user_content')

    if prompt_content:
        is_valid, error_details = validate_prompt_for_processing_mode(
            prompt_content, processing_mode
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_details
            )

    # STEP 3: Create flavor
    flavor = ServiceFlavor(
        service_id=service_id,
        **data
    )

    try:
        db.add(flavor)
        await db.commit()
        await db.refresh(flavor)

        # Load model and provider relationships
        from app.models.model import Model
        result = await db.execute(
            select(ServiceFlavor)
            .where(ServiceFlavor.id == flavor.id)
            .options(
                joinedload(ServiceFlavor.model).joinedload(Model.provider)
            )
        )
        flavor = result.scalar_one()

        return flavor
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating flavor: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create flavor: {str(e)}"
        )


# PATCH route alias for flavor edit (frontend calls this path)
@router.patch(
    "/services/{service_id}/flavors/{flavor_id}",
    response_model=ServiceFlavorResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}}
)
async def update_flavor_alias(
    service_id: UUID,
    flavor_id: UUID,
    flavor_update: ServiceFlavorUpdate,
    db: AsyncSession = Depends(get_db)
) -> ServiceFlavorResponse:
    """
    Update flavor configuration (alias route for frontend compatibility).

    This endpoint delegates to the main PATCH /flavors/{flavor_id} endpoint.

    - **service_id**: Service UUID (for path consistency)
    - **flavor_id**: UUID of the flavor
    - **flavor_update**: Fields to update
    """
    from app.services.flavor_service import FlavorService

    # Verify flavor belongs to service
    flavor = await FlavorService.get_flavor(db, flavor_id)
    if not flavor:
        raise HTTPException(status_code=404, detail="Flavor not found")
    if flavor.service_id != service_id:
        raise HTTPException(status_code=404, detail="Flavor does not belong to this service")

    # Perform update
    updated_flavor = await FlavorService.update_flavor(db, flavor_id, flavor_update)

    # Build ModelInfo with provider_name and token limits
    model_info = None
    if updated_flavor.model:
        provider_name = updated_flavor.model.provider.name if updated_flavor.model.provider else "Unknown"
        model_info = {
            "id": updated_flavor.model.id,
            "model_name": updated_flavor.model.model_name,
            "model_identifier": updated_flavor.model.model_identifier,
            "provider_id": updated_flavor.model.provider_id,
            "provider_name": provider_name,
            "context_length": updated_flavor.model.context_length,
            "max_generation_length": updated_flavor.model.max_generation_length,
            "security_level": updated_flavor.model.security_level,
        }

    # Convert to response model with prompt names
    response_data = ServiceFlavorResponse.model_validate(updated_flavor)
    response_data.model = model_info
    response_data.system_prompt_name = updated_flavor.system_prompt.name if updated_flavor.system_prompt else None
    response_data.user_prompt_template_name = updated_flavor.user_prompt_template.name if updated_flavor.user_prompt_template else None
    response_data.reduce_prompt_name = updated_flavor.reduce_prompt.name if updated_flavor.reduce_prompt else None
    response_data.placeholder_extraction_prompt_name = updated_flavor.placeholder_extraction_prompt.name if updated_flavor.placeholder_extraction_prompt else None
    response_data.categorization_prompt_name = updated_flavor.categorization_prompt.name if updated_flavor.categorization_prompt else None

    return response_data


@router.post(
    "/services/{service_id}/execute",
    response_model=ServiceExecuteResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def execute_service(
    service_id: UUID,
    request: ServiceExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a service with optional flavor selection.

    Accepts JSON request body with:
    - input: string or object (service-specific input)
    - flavor_id: optional UUID to use specific flavor
    - flavor_name: optional string to resolve flavor by name
    - metadata: optional metadata

    If neither flavor_id nor flavor_name provided, uses default flavor.

    Includes pre-execution context validation with auto-fallback.
    """
    from fastapi.responses import JSONResponse
    from app.http_server.celery_app import process_task
    from app.services.job_service import job_service
    from app.services.service_service import service_service
    from app.services.flavor_service import FlavorService
    from app.services.provider_service import provider_service

    # Get service
    service = await service_service.get_service_by_id(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Resolve flavor (by name, by ID, or default)
    flavor = None
    if request.flavor_name:
        flavor = await FlavorService.get_flavor_by_name(db, service_id, request.flavor_name)
        if not flavor:
            raise HTTPException(
                status_code=404,
                detail=f"Flavor '{request.flavor_name}' not found for this service"
            )
    elif request.flavor_id:
        flavor = await FlavorService.get_flavor(db, request.flavor_id)
        if flavor.service_id != service_id:
            raise HTTPException(
                status_code=404,
                detail="Flavor does not belong to this service"
            )
    else:
        # Use default flavor
        flavor = await FlavorService.get_default_flavor(db, service_id)
        if not flavor:
            raise HTTPException(
                status_code=400,
                detail="No default flavor configured for this service"
            )

    # Check if flavor is active
    if not flavor.is_active:
        error_response = ExecutionErrorResponse(
            detail="Selected flavor is inactive",
            error_code="FLAVOR_INACTIVE",
            flavor_id=str(flavor.id),
            flavor_name=flavor.name
        )
        return JSONResponse(status_code=400, content=error_response.model_dump())

    # Context validation and fallback logic
    original_flavor = None
    fallback_applied = False
    fallback_reason = None
    input_tokens = None
    context_available = None

    content = request.input

    # Validate context (skip for iterative mode - content will be chunked)
    fits, input_tokens, context_available = await _validate_context(flavor, content)

    # Iterative mode can handle any input size via chunking
    if not fits and flavor.processing_mode != "iterative":
        # Check if explicit fallback flavor is configured
        if flavor.fallback_flavor_id:
            # Load the explicit fallback flavor
            fallback_flavor = await FlavorService.get_flavor(db, flavor.fallback_flavor_id)
            if not fallback_flavor:
                error_response = ExecutionErrorResponse(
                    detail="Configured fallback flavor not found",
                    error_code="FALLBACK_FLAVOR_NOT_FOUND",
                    original_flavor_id=str(flavor.id),
                    suggestion="Update fallback_flavor_id to a valid flavor"
                )
                return JSONResponse(status_code=400, content=error_response.model_dump())

            if not fallback_flavor.is_active:
                error_response = ExecutionErrorResponse(
                    detail=f"Fallback flavor '{fallback_flavor.name}' is inactive",
                    error_code="FALLBACK_FLAVOR_INACTIVE",
                    original_flavor_id=str(flavor.id),
                    flavor_id=str(fallback_flavor.id),
                    flavor_name=fallback_flavor.name
                )
                return JSONResponse(status_code=400, content=error_response.model_dump())

            logger.info(
                f"Fallback: {flavor.name} -> {fallback_flavor.name} "
                f"(input: {input_tokens} tokens, available: {context_available})"
            )
            original_flavor = flavor
            flavor = fallback_flavor
            fallback_applied = True
            fallback_reason = f"Input ({input_tokens} tokens) exceeds context limit ({context_available} available)"
        else:
            # No fallback configured
            error_response = ExecutionErrorResponse(
                detail="Input exceeds context window",
                error_code="CONTEXT_EXCEEDED",
                input_tokens=input_tokens,
                available_tokens=context_available,
                suggestion="Configure a fallback_flavor_id with larger context or reduce input size"
            )
            return JSONResponse(status_code=400, content=error_response.model_dump())

    # Validate model has required token limits configured
    if not flavor.model.context_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{flavor.model.model_name}' is missing context_length configuration. "
                   f"Please configure token limits on the model before executing jobs."
        )
    if not flavor.model.max_generation_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{flavor.model.model_name}' is missing max_generation_length configuration. "
                   f"Please configure token limits on the model before executing jobs."
        )

    # Resolve tokenizer using TokenizerManager
    tokenizer = resolve_tokenizer_for_flavor(flavor)

    # Get decrypted API key from provider
    provider_id = flavor.model.provider_id
    decrypted_key = await provider_service.get_decrypted_api_key(db, provider_id)

    # Get extraction fields from templates (for metadata extraction)
    extraction_fields = await _get_extraction_fields(db, service_id)

    # Build task_data using model's direct limits
    # Use sensible defaults for processing parameters when flavor values are None
    task_data = {
        "backend": flavor.model.provider.provider_type,
        "providerConfig": {
            "api_url": flavor.model.provider.api_base_url,
            "api_key": decrypted_key,
            "provider_type": flavor.model.provider.provider_type,
        },
        "name": service.name,
        "type": service.service_type,
        "backendParams": {
            "modelName": flavor.model.model_identifier,
            # Model token limits (validated above)
            "totalContextLength": flavor.model.context_length,
            "maxGenerationLength": flavor.model.max_generation_length,
            "tokenizerClass": flavor.model.tokenizer_class,
            "tokenizer": tokenizer,
            "temperature": flavor.temperature,
            "top_p": flavor.top_p,
            "createNewTurnAfter": flavor.create_new_turn_after or 500,  # Default: 500 tokens
            "summaryTurns": flavor.summary_turns or 3,  # Default: 3 turns for summary context
            "maxNewTurns": flavor.max_new_turns or 10,  # Default: 10 turns per batch
            "reduceSummary": flavor.reduce_summary,
            "consolidateSummary": flavor.consolidate_summary,
            "reduce_prompt": flavor.reduce_prompt.name if flavor.reduce_prompt else None,
            "type": flavor.output_type,
            # Processing mode
            "processing_mode": flavor.processing_mode,
            # Cost estimation rate
            "estimated_cost_per_1k_tokens": flavor.estimated_cost_per_1k_tokens,
        },
        # Derive fields from prompt placeholder count
        "fields": count_placeholders(flavor.prompt_user_content or ""),
        "content": content,
        "prompt_system_content": flavor.prompt_system_content,
        "prompt_user_content": flavor.prompt_user_content,
        "prompt_reduce_content": flavor.prompt_reduce_content,
        # Placeholder extraction configuration
        "prompt_extraction_content": (
            flavor.placeholder_extraction_prompt.content
            if flavor.placeholder_extraction_prompt else None
        ),
        "extraction_fields": extraction_fields,
        # Categorization prompt configuration
        "prompt_categorization_content": (
            flavor.categorization_prompt.content
            if flavor.categorization_prompt else None
        ),
        # Context data (tags, metadata, etc. passed at execution time)
        "context": request.context,
        # Failover configuration for automatic retry on specific errors
        "failoverConfig": {
            "failover_enabled": flavor.failover_enabled,
            "failover_flavor_id": str(flavor.failover_flavor_id) if flavor.failover_flavor_id else None,
            "failover_on_timeout": flavor.failover_on_timeout,
            "failover_on_rate_limit": flavor.failover_on_rate_limit,
            "failover_on_model_error": flavor.failover_on_model_error,
            "failover_on_content_filter": flavor.failover_on_content_filter,
            "max_failover_depth": flavor.max_failover_depth,
        },
        # Track flavor ID for failover tracking
        "flavor_id": str(flavor.id),
    }

    # Fix race condition - create job BEFORE dispatching Celery task
    # Generate Celery task ID upfront so we can create the job record first
    celery_task_id = str(uuid_module.uuid4())

    # Create job record FIRST
    job = await job_service.create_job(
        db=db,
        service_id=service_id,
        flavor_id=flavor.id,
        celery_task_id=celery_task_id,
        organization_id=None,  # TODO: Extract from auth
        input_file_name=None,
        input_preview=content[:500] if isinstance(content, str) else str(content)[:500],
        # Fallback tracking
        fallback_applied=fallback_applied,
        original_flavor_id=original_flavor.id if original_flavor else None,
        original_flavor_name=original_flavor.name if original_flavor else None,
        fallback_reason=fallback_reason,
        fallback_input_tokens=input_tokens,
        fallback_context_available=context_available,
        # TTL configuration from flavor
        default_ttl_seconds=flavor.default_ttl_seconds,
    )

    # Add job_id and organization_id to task_data for progress broadcasting
    task_data["job_id"] = str(job.id)
    task_data["organization_id"] = job.organization_id

    # Now dispatch Celery task with the predetermined task_id and flavor priority
    # Invert priority for Redis: higher celery priority = processed first
    # So flavor.priority=0 (urgent) becomes celery_priority=9 (highest)
    celery_priority = 9 - flavor.priority
    process_task.apply_async(
        args=[task_data],
        task_id=celery_task_id,
        priority=celery_priority
    )

    return ServiceExecuteResponse(
        job_id=str(job.id),
        status="queued",
        service_id=str(service_id),
        service_name=service.name,
        flavor_id=str(flavor.id),
        flavor_name=flavor.name,
        created_at=job.created_at.isoformat(),
        estimated_completion_time=None,
        # Fallback tracking
        fallback_applied=fallback_applied,
        original_flavor_id=str(original_flavor.id) if original_flavor else None,
        original_flavor_name=original_flavor.name if original_flavor else None,
        fallback_reason=fallback_reason,
        input_tokens=input_tokens,
        context_available=context_available,
    )


async def _execute_with_file_internal(
    service_id: UUID,
    flavor_id: str,
    file: Optional[UploadFile],
    synthetic_template: Optional[str],
    temperature: Optional[float],
    top_p: Optional[float],
    organization_id: Optional[str],
    db,
    context_data: Optional[Dict[str, Any]] = None,
):
    """
    Internal implementation for file-based execution with context validation.
    """
    from pathlib import Path
    from fastapi.responses import JSONResponse
    from app.http_server.celery_app import process_task
    from app.services.job_service import job_service
    from app.services.flavor_service import FlavorService
    from app.services.provider_service import provider_service

    # Validate input - must have exactly one
    if file and synthetic_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either file or synthetic_template, not both"
        )
    if not file and not synthetic_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either file or synthetic_template"
        )

    # Get service
    service = await service_service.get_service_by_id(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Get flavor
    flavor = await FlavorService.get_flavor(db, UUID(flavor_id))
    if not flavor:
        raise HTTPException(status_code=404, detail="Flavor not found")
    if flavor.service_id != service_id:
        raise HTTPException(status_code=404, detail="Flavor does not belong to this service")

    # Check if flavor is active
    if not flavor.is_active:
        error_response = ExecutionErrorResponse(
            detail="Selected flavor is inactive",
            error_code="FLAVOR_INACTIVE",
            flavor_id=str(flavor.id),
            flavor_name=flavor.name
        )
        return JSONResponse(status_code=400, content=error_response.model_dump())

    # Get content from file or synthetic template
    input_file_name = None
    if synthetic_template:
        # Security: validate filename to prevent path traversal
        if "/" in synthetic_template or "\\" in synthetic_template or ".." in synthetic_template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid template filename"
            )
        templates_dir = Path(__file__).parent.parent.parent.parent / "tests/data/conversations/synthetic"
        template_path = templates_dir / synthetic_template
        if not template_path.exists() or not template_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Synthetic template '{synthetic_template}' not found"
            )
        content = template_path.read_text(encoding="utf-8")
        input_file_name = f"synthetic:{synthetic_template}"
    else:
        content = (await file.read()).decode("utf-8")
        input_file_name = file.filename

    # Context validation and fallback logic
    original_flavor = None
    fallback_applied = False
    fallback_reason = None
    input_tokens = None
    context_available = None

    # Validate context (skip for iterative mode - content will be chunked)
    fits, input_tokens, context_available = await _validate_context(flavor, content)

    # Iterative mode can handle any input size via chunking
    if not fits and flavor.processing_mode != "iterative":
        # Check if explicit fallback flavor is configured
        if flavor.fallback_flavor_id:
            # Load the explicit fallback flavor
            fallback_flavor = await FlavorService.get_flavor(db, flavor.fallback_flavor_id)
            if not fallback_flavor:
                error_response = ExecutionErrorResponse(
                    detail="Configured fallback flavor not found",
                    error_code="FALLBACK_FLAVOR_NOT_FOUND",
                    original_flavor_id=str(flavor.id),
                    suggestion="Update fallback_flavor_id to a valid flavor"
                )
                return JSONResponse(status_code=400, content=error_response.model_dump())

            if not fallback_flavor.is_active:
                error_response = ExecutionErrorResponse(
                    detail=f"Fallback flavor '{fallback_flavor.name}' is inactive",
                    error_code="FALLBACK_FLAVOR_INACTIVE",
                    original_flavor_id=str(flavor.id),
                    flavor_id=str(fallback_flavor.id),
                    flavor_name=fallback_flavor.name
                )
                return JSONResponse(status_code=400, content=error_response.model_dump())

            logger.info(
                f"Fallback: {flavor.name} -> {fallback_flavor.name} "
                f"(input: {input_tokens} tokens, available: {context_available})"
            )
            original_flavor = flavor
            flavor = fallback_flavor
            fallback_applied = True
            fallback_reason = f"Input ({input_tokens} tokens) exceeds context limit ({context_available} available)"
        else:
            # No fallback configured
            error_response = ExecutionErrorResponse(
                detail="Input exceeds context window",
                error_code="CONTEXT_EXCEEDED",
                input_tokens=input_tokens,
                available_tokens=context_available,
                suggestion="Configure a fallback_flavor_id with larger context or reduce input size"
            )
            return JSONResponse(status_code=400, content=error_response.model_dump())

    # Apply temperature/top_p overrides
    effective_temperature = temperature if temperature is not None else flavor.temperature
    effective_top_p = top_p if top_p is not None else flavor.top_p

    # Validate model has required token limits configured
    if not flavor.model.context_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{flavor.model.model_name}' is missing context_length configuration. "
                   f"Please configure token limits on the model before executing jobs."
        )
    if not flavor.model.max_generation_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{flavor.model.model_name}' is missing max_generation_length configuration. "
                   f"Please configure token limits on the model before executing jobs."
        )

    # Resolve tokenizer using TokenizerManager
    tokenizer = resolve_tokenizer_for_flavor(flavor)

    # Get decrypted API key from provider
    provider_id = flavor.model.provider_id
    decrypted_key = await provider_service.get_decrypted_api_key(db, provider_id)

    # Get extraction fields from templates (for metadata extraction)
    extraction_fields = await _get_extraction_fields(db, service_id)

    # Build task_data using model's direct limits
    # Use sensible defaults for processing parameters when flavor values are None
    task_data = {
        "backend": flavor.model.provider.provider_type,
        "providerConfig": {
            "api_url": flavor.model.provider.api_base_url,
            "api_key": decrypted_key,
            "provider_type": flavor.model.provider.provider_type,
        },
        "name": service.name,
        "type": service.service_type,
        "backendParams": {
            "modelName": flavor.model.model_identifier,
            # Model token limits (validated above)
            "totalContextLength": flavor.model.context_length,
            "maxGenerationLength": flavor.model.max_generation_length,
            "tokenizerClass": flavor.model.tokenizer_class,
            "tokenizer": tokenizer,
            "temperature": effective_temperature,
            "top_p": effective_top_p,
            "createNewTurnAfter": flavor.create_new_turn_after or 500,  # Default: 500 tokens
            "summaryTurns": flavor.summary_turns or 3,  # Default: 3 turns for summary context
            "maxNewTurns": flavor.max_new_turns or 10,  # Default: 10 turns per batch
            "reduceSummary": flavor.reduce_summary,
            "consolidateSummary": flavor.consolidate_summary,
            "reduce_prompt": flavor.reduce_prompt.name if flavor.reduce_prompt else None,
            "type": flavor.output_type,
            # Processing mode
            "processing_mode": flavor.processing_mode,
            # Cost estimation rate
            "estimated_cost_per_1k_tokens": flavor.estimated_cost_per_1k_tokens,
        },
        # Derive fields from prompt placeholder count
        "fields": count_placeholders(flavor.prompt_user_content or ""),
        "content": content,
        "prompt_system_content": flavor.prompt_system_content,
        "prompt_user_content": flavor.prompt_user_content,
        "prompt_reduce_content": flavor.prompt_reduce_content,
        # Placeholder extraction configuration
        "prompt_extraction_content": (
            flavor.placeholder_extraction_prompt.content
            if flavor.placeholder_extraction_prompt else None
        ),
        "extraction_fields": extraction_fields,
        # Categorization prompt configuration
        "prompt_categorization_content": (
            flavor.categorization_prompt.content
            if flavor.categorization_prompt else None
        ),
        # Context data (tags, metadata, etc. passed at execution time)
        # Note: File upload endpoint doesn't support context yet
        "context": context_data,
        # Failover configuration for automatic retry on specific errors
        "failoverConfig": {
            "failover_enabled": flavor.failover_enabled,
            "failover_flavor_id": str(flavor.failover_flavor_id) if flavor.failover_flavor_id else None,
            "failover_on_timeout": flavor.failover_on_timeout,
            "failover_on_rate_limit": flavor.failover_on_rate_limit,
            "failover_on_model_error": flavor.failover_on_model_error,
            "failover_on_content_filter": flavor.failover_on_content_filter,
            "max_failover_depth": flavor.max_failover_depth,
        },
        # Track flavor ID for failover tracking
        "flavor_id": str(flavor.id),
    }

    # Fix race condition - create job BEFORE dispatching Celery task
    # Generate Celery task ID upfront so we can create the job record first
    celery_task_id = str(uuid_module.uuid4())

    # Create job record FIRST
    job = await job_service.create_job(
        db=db,
        service_id=service_id,
        flavor_id=flavor.id,
        celery_task_id=celery_task_id,
        organization_id=organization_id,
        input_file_name=input_file_name,
        input_preview=content[:500] if content else "",
        # Fallback tracking
        fallback_applied=fallback_applied,
        original_flavor_id=original_flavor.id if original_flavor else None,
        original_flavor_name=original_flavor.name if original_flavor else None,
        fallback_reason=fallback_reason,
        fallback_input_tokens=input_tokens,
        fallback_context_available=context_available,
        # TTL configuration from flavor
        default_ttl_seconds=flavor.default_ttl_seconds,
    )

    # Add job_id and organization_id to task_data for progress broadcasting
    task_data["job_id"] = str(job.id)
    task_data["organization_id"] = job.organization_id

    # Now dispatch Celery task with the predetermined task_id and flavor priority
    # Invert priority for Redis: higher celery priority = processed first
    # So flavor.priority=0 (urgent) becomes celery_priority=9 (highest)
    celery_priority = 9 - flavor.priority
    process_task.apply_async(
        args=[task_data],
        task_id=celery_task_id,
        priority=celery_priority
    )

    return ServiceExecuteResponse(
        job_id=str(job.id),
        status="queued",
        service_id=str(service_id),
        service_name=service.name,
        flavor_id=str(flavor.id),
        flavor_name=flavor.name,
        created_at=job.created_at.isoformat(),
        estimated_completion_time=None,
        # Fallback tracking
        fallback_applied=fallback_applied,
        original_flavor_id=str(original_flavor.id) if original_flavor else None,
        original_flavor_name=original_flavor.name if original_flavor else None,
        fallback_reason=fallback_reason,
        input_tokens=input_tokens,
        context_available=context_available,
    )


@router.post(
    "/services/{service_id}/run",
    response_model=ServiceExecuteResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def run_service_with_file(
    service_id: UUID,
    flavor_id: str = Form(...),
    file: Optional[UploadFile] = File(None),
    synthetic_template: Optional[str] = Form(None),
    temperature: Optional[float] = Form(None),
    top_p: Optional[float] = Form(None),
    organization_id: Optional[str] = Form(None),
    context: Optional[str] = Form(None, description="JSON-encoded context data for categorization (tags, metadata)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Primary endpoint for file-based service execution.

    Supports:
    - File uploads (text files)
    - Synthetic templates
    - Context data for categorization (tags, metadata)

    Accepts multipart/form-data with:
    - flavor_id: UUID of flavor to use (required)
    - file: File upload (optional, mutually exclusive with synthetic_template)
    - synthetic_template: Synthetic template filename (optional, mutually exclusive with file)
    - temperature: Override flavor temperature (optional)
    - top_p: Override flavor top_p (optional)
    - organization_id: Organization context (optional)
    - context: JSON-encoded context data for categorization (optional)

    Either file OR synthetic_template must be provided, not both.

    Returns job info with fallback details if fallback was applied.
    """
    import json
    # Parse context JSON if provided
    context_data = None
    if context:
        try:
            context_data = json.loads(context)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON in context field"
            )

    return await _execute_with_file_internal(
        service_id=service_id,
        flavor_id=flavor_id,
        file=file,
        synthetic_template=synthetic_template,
        temperature=temperature,
        top_p=top_p,
        organization_id=organization_id,
        db=db,
        context_data=context_data,
    )


@router.get(
    "/services/{service_id}/flavors/{flavor_id}/fallback-available",
    response_model=FallbackAvailabilityResponse,
)
async def check_fallback_available(
    service_id: UUID,
    flavor_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Check if an iterative fallback flavor is available for the specified flavor.

    Returns whether a fallback exists and its details if available.
    """
    from app.services.flavor_service import FlavorService

    # Verify service exists
    service = await service_service.get_service_by_id(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Verify flavor exists and belongs to service
    flavor = await FlavorService.get_flavor(db, flavor_id)
    if not flavor:
        raise HTTPException(status_code=404, detail="Flavor not found")
    if flavor.service_id != service_id:
        raise HTTPException(status_code=404, detail="Flavor does not belong to this service")

    # Find fallback
    fallback_flavor = await FlavorService.find_iterative_fallback(db, service_id, flavor_id)

    if fallback_flavor:
        return FallbackAvailabilityResponse(
            fallback_available=True,
            fallback_flavor_id=str(fallback_flavor.id),
            fallback_flavor_name=fallback_flavor.name,
        )
    else:
        return FallbackAvailabilityResponse(
            fallback_available=False,
            fallback_flavor_id=None,
            fallback_flavor_name=None,
            reason="No active iterative flavor in this service",
        )


@router.post(
    "/services/{service_id}/validate-execution",
    response_model=ExecutionValidationResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def validate_execution(
    service_id: UUID,
    flavor_id: str = Form(...),
    file: Optional[UploadFile] = File(None),
    synthetic_template: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Dry run: validate content fits within flavor's context limits.

    - Iterative flavors: always valid (content is chunked automatically)
    - Single-pass flavors: checks if input + prompts fit in context window
    """
    from pathlib import Path
    from app.services.flavor_service import FlavorService

    # Validate input - must have exactly one
    if file and synthetic_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either file or synthetic_template, not both"
        )
    if not file and not synthetic_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either file or synthetic_template"
        )

    # Get service
    service = await service_service.get_service_by_id(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Get flavor with prompts
    flavor = await FlavorService.get_flavor(db, UUID(flavor_id))
    if not flavor:
        raise HTTPException(status_code=404, detail="Flavor not found")

    # Get content
    if synthetic_template:
        if "/" in synthetic_template or "\\" in synthetic_template or ".." in synthetic_template:
            raise HTTPException(status_code=400, detail="Invalid template filename")
        templates_dir = Path(__file__).parent.parent.parent.parent / "tests/data/conversations/synthetic"
        template_path = templates_dir / synthetic_template
        if not template_path.exists():
            raise HTTPException(status_code=404, detail=f"Synthetic template '{synthetic_template}' not found")
        content = template_path.read_text(encoding="utf-8")
    else:
        content = (await file.read()).decode("utf-8")

    # Common setup for both modes
    context_length = flavor.model.context_length or 0
    max_gen_length = flavor.model.max_generation_length or 0
    # Available context = total context - reserved for generation
    context_available = context_length - max_gen_length

    try:
        manager = TokenizerManager.get_instance()
        input_tokens = manager.count_tokens(flavor.model, content)
    except Exception as e:
        logger.warning(f"Tokenizer count failed: {e}")
        input_tokens = len(content) // 4

    # Iterative mode: always valid, but warn if reduce/extraction/categorization may exceed context
    if flavor.processing_mode == "iterative":
        warnings = []
        half_context = context_available * 0.5

        # Check reduce phase if enabled
        if flavor.reduce_summary and flavor.prompt_reduce_content:
            try:
                reduce_prompt_tokens = manager.count_tokens(flavor.model, flavor.prompt_reduce_content)
            except Exception:
                reduce_prompt_tokens = 500

            # Reduce needs: reduce_prompt + accumulated output (~50% of input) + max_gen
            reduce_total = reduce_prompt_tokens + int(input_tokens * 0.5)

            if reduce_total > context_available:
                warnings.append(f"Reduce phase may exceed context: {reduce_total} tokens needed, {context_available} available")

        # Check extraction phase if enabled and input > 50% of context
        if flavor.placeholder_extraction_prompt_id and input_tokens > half_context:
            warnings.append(f"Extraction: input ({input_tokens} tokens) exceeds 50% of context ({int(half_context)} tokens)")

        # Check categorization phase if enabled and input > 50% of context
        if flavor.categorization_prompt_id and input_tokens > half_context:
            warnings.append(f"Categorization: input ({input_tokens} tokens) exceeds 50% of context ({int(half_context)} tokens)")

        if warnings:
            return ExecutionValidationResponse(
                valid=True,
                warning="; ".join(warnings)
            )

        return ExecutionValidationResponse(valid=True)

    # Single-pass mode: count actual input tokens (content + prompts)
    try:
        prompt_tokens = 0
        if flavor.prompt_system_content:
            prompt_tokens += manager.count_tokens(flavor.model, flavor.prompt_system_content)
        if flavor.prompt_user_content:
            prompt_tokens += manager.count_tokens(flavor.model, flavor.prompt_user_content)
    except Exception as e:
        logger.warning(f"Tokenizer count failed for prompts: {e}")
        prompt_tokens = 500

    # Real input tokens = content + prompts
    total_input_tokens = input_tokens + prompt_tokens

    # Calculate cost if configured (based on input + estimated output)
    estimated_cost = None
    if flavor.estimated_cost_per_1k_tokens:
        # Estimate: input + half of max_gen as typical output
        estimated_total = total_input_tokens + (max_gen_length // 2)
        estimated_cost = round(estimated_total / 1000 * flavor.estimated_cost_per_1k_tokens, 6)

    # Check fit: input + max_gen must fit in context
    capacity_needed = total_input_tokens + max_gen_length
    fits = capacity_needed <= context_length
    close_to_limit = capacity_needed > context_length * 0.8 and fits

    if not fits:
        return ExecutionValidationResponse(
            valid=False,
            warning=f"Content too large ({total_input_tokens} input + {max_gen_length} max gen = {capacity_needed} tokens, context: {context_length})",
            input_tokens=total_input_tokens,
            max_generation=max_gen_length,
            context_length=context_length,
            estimated_cost=estimated_cost,
        )

    if close_to_limit:
        return ExecutionValidationResponse(
            valid=True,
            warning=f"Close to limit ({int(capacity_needed/context_length*100)}% of context)",
            input_tokens=total_input_tokens,
            max_generation=max_gen_length,
            context_length=context_length,
            estimated_cost=estimated_cost,
        )

    return ExecutionValidationResponse(
        valid=True,
        input_tokens=total_input_tokens,
        max_generation=max_gen_length,
        context_length=context_length,
        estimated_cost=estimated_cost,
    )


@router.get(
    "/services/{service_id}/flavor-stats",
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    }
)
async def get_service_flavor_stats(
    service_id: UUID,
    period: str = Query('24h', regex='^(24h|7d|30d|all)$'),
    db: AsyncSession = Depends(get_db)
):
    """
    Compare usage statistics across all flavors for a service.

    - **service_id**: Service UUID
    - **period**: Time period (24h, 7d, 30d, all)

    **Returns comprehensive comparison:**
    - Per-flavor statistics (requests, tokens, latency, cost)
    - Usage percentage per flavor
    - Service-wide totals
    """
    from app.services.flavor_analytics_service import FlavorAnalyticsService

    return await FlavorAnalyticsService.compare_service_flavors(db, service_id, period)


@router.get(
    "/services/{service_id}/stats",
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    }
)
async def get_service_stats(
    service_id: UUID,
    period: str = Query('24h', regex='^(24h|7d|30d|all)$'),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated statistics for a service across all flavors.

    - **service_id**: Service UUID
    - **period**: Time period (24h, 7d, 30d, all)

    **Returns comprehensive statistics:**
    - Total requests, success rate, tokens, cost
    - Average latency
    - Flavor breakdown with percentages
    - Time series data (hourly for 24h, daily otherwise)
    """
    from app.services.analytics_service import AnalyticsService

    return await AnalyticsService.get_service_stats(db, service_id, period)


# =============================================================================
# Failover Chain Endpoints
# =============================================================================

@router.get(
    "/services/{service_id}/flavors/{flavor_id}/failover-chain",
    response_model=FailoverChainResponse,
    responses={
        404: {"model": ErrorResponse},
    }
)
async def get_failover_chain(
    service_id: UUID,
    flavor_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> FailoverChainResponse:
    """
    Get the complete failover chain for a flavor.

    Returns the chain of flavors that would be used in failover scenarios,
    starting from the specified flavor and following failover_flavor_id links.

    - **service_id**: Service UUID
    - **flavor_id**: Flavor UUID

    **Response includes:**
    - chain: List of flavors with id, name, service_name, model_name, is_active, depth
    - max_depth: Maximum configured failover depth for the starting flavor
    - has_cycle: Whether a cycle was detected (should always be false for valid chains)
    """
    from app.services.failover_service import failover_service

    # Verify flavor exists and belongs to service
    flavor = await failover_service.get_flavor_by_id(db, flavor_id)
    if not flavor or flavor.service_id != service_id:
        raise HTTPException(status_code=404, detail="Flavor not found")

    chain, has_cycle = await failover_service.get_failover_chain(db, flavor_id)

    # Convert to response schema
    chain_items = [FailoverChainItem(**item) for item in chain]

    return FailoverChainResponse(
        chain=chain_items,
        max_depth=flavor.max_failover_depth,
        has_cycle=has_cycle
    )


@router.post(
    "/services/{service_id}/flavors/{flavor_id}/validate-failover",
    response_model=ValidateFailoverResponse,
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    }
)
async def validate_failover(
    service_id: UUID,
    flavor_id: UUID,
    request: ValidateFailoverRequest,
    db: AsyncSession = Depends(get_db)
) -> ValidateFailoverResponse:
    """
    Validate a proposed failover configuration.

    Checks whether setting the specified failover_flavor_id would create
    a cycle in the failover chain. Use this before updating a flavor's
    failover configuration.

    - **service_id**: Service UUID
    - **flavor_id**: Flavor UUID to configure
    - **failover_flavor_id**: Proposed failover target UUID

    **Response includes:**
    - valid: Whether the configuration is valid (no cycles)
    - error: Error message if invalid
    - chain_depth: Total depth of the chain if valid
    - chain_preview: List of flavor names that would be in the chain
    """
    from app.services.failover_service import failover_service

    # Verify flavor exists and belongs to service
    flavor = await failover_service.get_flavor_by_id(db, flavor_id)
    if not flavor or flavor.service_id != service_id:
        raise HTTPException(status_code=404, detail="Flavor not found")

    # Validate chain
    is_valid, error, depth, chain_preview = await failover_service.validate_failover_chain(
        db, flavor_id, request.failover_flavor_id
    )

    return ValidateFailoverResponse(
        valid=is_valid,
        error=error,
        chain_depth=depth,
        chain_preview=chain_preview
    )
