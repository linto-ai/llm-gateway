#!/usr/bin/env python3
"""
API endpoints for tokenizer management.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.models.model import Model
from app.schemas.tokenizer import (
    TokenizerDeleteResponse,
    TokenizerInfo,
    TokenizerListResponse,
    TokenizerPreloadResponse,
)
from app.services.tokenizer_manager import TokenizerManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tokenizers", tags=["tokenizers"])


@router.get(
    "",
    response_model=TokenizerListResponse,
    summary="List local tokenizers",
    description="List all tokenizers persisted locally on disk.",
)
async def list_tokenizers() -> TokenizerListResponse:
    """
    List all tokenizers persisted locally.

    Returns information about each tokenizer including:
    - ID (filesystem-safe format)
    - Source repository
    - Type (huggingface or tiktoken)
    - Size in bytes
    - Creation timestamp
    """
    manager = TokenizerManager.get_instance()

    tokenizers = manager.list_local_tokenizers()
    storage_info = manager.get_storage_info()

    return TokenizerListResponse(
        tokenizers=[
            TokenizerInfo(
                id=t.id,
                source_repo=t.source_repo,
                type=t.type,
                size_bytes=t.size_bytes,
                created_at=t.created_at,
            )
            for t in tokenizers
        ],
        storage_path=storage_info["storage_path"],
        total_size_bytes=storage_info["total_size_bytes"],
    )


@router.post(
    "/preload/{model_id}",
    response_model=TokenizerPreloadResponse,
    summary="Preload tokenizer for a model",
    description="Force preload tokenizer for a specific model. Downloads and persists if needed.",
    responses={
        404: {"description": "Model not found"},
        500: {"description": "Failed to load tokenizer"},
    },
)
async def preload_tokenizer(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TokenizerPreloadResponse:
    """
    Force preload tokenizer for a specific model.

    This endpoint will:
    1. Look up the model by ID
    2. Resolve the appropriate tokenizer
    3. Download and persist if not already cached
    4. Return the preload result
    """
    # Get model
    result = await db.execute(select(Model).where(Model.id == model_id))
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    manager = TokenizerManager.get_instance()

    try:
        preload_result = manager.preload_tokenizer(model)

        if not preload_result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=preload_result.message,
            )

        return TokenizerPreloadResponse(
            success=preload_result.success,
            model_identifier=preload_result.model_identifier,
            tokenizer_id=preload_result.tokenizer_id,
            tokenizer_type=preload_result.tokenizer_type,
            cached=preload_result.cached,
            message=preload_result.message,
        )
    except Exception as e:
        logger.error(f"Failed to preload tokenizer for model {model_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load tokenizer: {str(e)}",
        )


@router.post(
    "/preload-repo",
    response_model=TokenizerPreloadResponse,
    summary="Preload tokenizer by HuggingFace repo",
    description="Download and persist a tokenizer directly from a HuggingFace repository.",
    responses={
        400: {"description": "Invalid repository"},
        500: {"description": "Failed to load tokenizer"},
    },
)
async def preload_tokenizer_by_repo(
    repo: str = Query(..., description="HuggingFace repository path (e.g., 'meta-llama/Llama-3.1-8B-Instruct')"),
) -> TokenizerPreloadResponse:
    """
    Preload a tokenizer directly from a HuggingFace repository.

    This endpoint will:
    1. Download the tokenizer from HuggingFace
    2. Persist it to local storage
    3. Return the preload result

    Args:
        repo: HuggingFace repository path (e.g., "meta-llama/Llama-3.1-8B-Instruct")
    """
    if not repo or "/" not in repo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid repository format. Expected: 'org/model-name'",
        )

    manager = TokenizerManager.get_instance()

    try:
        # Check if already cached
        local_path = manager._get_local_path(repo)
        cached = local_path.exists()

        if cached:
            # Verify it loads correctly
            tokenizer = manager._load_from_local(repo)
            if tokenizer:
                return TokenizerPreloadResponse(
                    success=True,
                    model_identifier=repo,
                    tokenizer_id=repo,
                    tokenizer_type="huggingface",
                    cached=True,
                    message="Tokenizer already cached locally",
                )

        # Download and save
        manager._download_and_save(repo)
        return TokenizerPreloadResponse(
            success=True,
            model_identifier=repo,
            tokenizer_id=repo,
            tokenizer_type="huggingface",
            cached=False,
            message="Tokenizer downloaded and persisted",
        )
    except Exception as e:
        logger.error(f"Failed to preload tokenizer from repo {repo}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load tokenizer: {str(e)}",
        )


@router.delete(
    "/{tokenizer_id:path}",
    response_model=TokenizerDeleteResponse,
    summary="Delete a tokenizer",
    description="Delete a tokenizer from local storage.",
    responses={
        404: {"description": "Tokenizer not found"},
    },
)
async def delete_tokenizer(tokenizer_id: str) -> TokenizerDeleteResponse:
    """
    Delete a tokenizer from local storage.

    The tokenizer_id should be in filesystem-safe format (e.g., "meta-llama--Llama-3.1-8B-Instruct")
    or the original format with slashes (e.g., "meta-llama/Llama-3.1-8B-Instruct").
    """
    manager = TokenizerManager.get_instance()

    try:
        delete_result = manager.delete_tokenizer(tokenizer_id)
        return TokenizerDeleteResponse(
            deleted=delete_result.deleted,
            freed_bytes=delete_result.freed_bytes,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tokenizer not found",
        )
    except Exception as e:
        logger.error(f"Failed to delete tokenizer {tokenizer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tokenizer: {str(e)}",
        )
