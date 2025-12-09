"""HuggingFace API router for tokenizer lookups."""
import logging
from fastapi import APIRouter, HTTPException, status

from app.services.huggingface_service import huggingface_service
from app.schemas.huggingface import HuggingFaceTokenizerResponse
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/huggingface", tags=["huggingface"])


@router.get(
    "/tokenizer/{repo_path:path}",
    response_model=HuggingFaceTokenizerResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_tokenizer_info(repo_path: str) -> HuggingFaceTokenizerResponse:
    """
    Fetch tokenizer info from a HuggingFace repository.

    - **repo_path**: HuggingFace repository path, e.g., "mistralai/Mistral-Small-3.1-24B-Instruct-2503"

    Returns tokenizer class and name if found, otherwise returns found=False.
    """
    try:
        result = await huggingface_service.get_tokenizer_info(repo_path)

        if result.get("error") and "HTTP 404" in result["error"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository not found or private: {repo_path}",
            )

        return HuggingFaceTokenizerResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching tokenizer info for {repo_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"HuggingFace API error: {str(e)}",
        )


router_name = "huggingface"
