#!/usr/bin/env python3
"""Chat completions endpoint - stateless streaming proxy.

Resolves flavor configuration, injects context into the system prompt template,
and streams tokens via SSE from the upstream LLM provider.
"""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.dependencies import get_db
from app.backends.openai_adapter import OpenAIAdapter
from app.models.model import Model
from app.models.service_flavor import ServiceFlavor
from app.schemas.chat import ChatCompletionRequest, ChatContext
from app.services.provider_service import provider_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def resolve_system_prompt(template: str, context: ChatContext) -> str:
    """Replace placeholders in system prompt template with context values.

    Supports the following placeholders:
    - {transcript}: Full conversation transcript (required in context)
    - {summary_section}: Conditional block, included only when summary is present
    - {summary}: Raw summary text
    - {conversation_name}, {date}, etc.: From context.metadata
    """
    result = template

    # Replace transcript
    result = result.replace("{transcript}", context.transcript or "")

    # Handle summary section conditionally
    if context.summary:
        summary_section = (
            f"Below is a summary that was generated from this transcript:\n"
            f"---\n{context.summary}\n---"
        )
        result = result.replace("{summary_section}", summary_section)
        result = result.replace("{summary}", context.summary)
    else:
        result = result.replace("{summary_section}", "")
        result = result.replace("{summary}", "")

    # Replace metadata fields
    if context.metadata:
        for key, value in context.metadata.items():
            result = result.replace(f"{{{key}}}", str(value) if value else "")

    return result


async def _load_flavor_with_relations(
    db: AsyncSession, flavor_id: UUID
) -> ServiceFlavor:
    """Load a flavor with model and provider relationships eagerly loaded."""
    result = await db.execute(
        select(ServiceFlavor)
        .where(ServiceFlavor.id == flavor_id)
        .where(ServiceFlavor.is_active.is_(True))
        .options(
            joinedload(ServiceFlavor.model).joinedload(Model.provider),
            joinedload(ServiceFlavor.service),
        )
    )
    return result.scalar_one_or_none()


async def sse_generator(adapter: OpenAIAdapter, messages: list[dict], **kwargs):
    """Async generator that yields SSE-formatted events from the adapter stream."""
    try:
        async for content, usage in adapter.stream_chat(messages, **kwargs):
            if usage:
                yield f"event: done\ndata: {json.dumps({'usage': usage})}\n\n"
            elif content:
                yield f"event: token\ndata: {json.dumps({'content': content})}\n\n"
    except Exception as e:
        logger.error(f"Chat streaming error: {e}")
        yield f"event: error\ndata: {json.dumps({'error': 'Streaming error'})}\n\n"


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Stream chat completion tokens via SSE.

    Resolves flavor configuration, builds the system prompt from the template
    and provided context, then streams tokens from the upstream LLM provider.

    - **flavor_id**: UUID of the flavor to use (determines model, provider, prompts)
    - **messages**: Conversation history (user/assistant turns only)
    - **context**: Transcript and optional summary injected into system prompt
    - **max_tokens**: Optional override for max generation length
    """
    # 1. Load flavor with model + provider
    flavor = await _load_flavor_with_relations(db, request.flavor_id)
    if not flavor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flavor not found or inactive",
        )

    if not flavor.model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not configured",
        )

    if not flavor.model.provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not configured",
        )

    # 2. Get decrypted API key
    decrypted_key = await provider_service.get_decrypted_api_key(
        db, flavor.model.provider_id
    )
    if not decrypted_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key configuration error",
        )

    # 3. Resolve system prompt template with context
    system_prompt_template = flavor.prompt_system_content or ""
    if not system_prompt_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flavor has no system prompt template configured",
        )

    resolved_system_prompt = resolve_system_prompt(
        system_prompt_template, request.context
    )

    # 4. Build messages array: system prompt + user/assistant turns
    messages = [{"role": "system", "content": resolved_system_prompt}]
    for msg in request.messages:
        messages.append({"role": msg.role, "content": msg.content})

    # 5. Create OpenAI adapter with task_data matching existing pattern
    max_gen_length = request.max_tokens or flavor.model.max_generation_length
    task_data = {
        "providerConfig": {
            "api_url": flavor.model.provider.api_base_url,
            "api_key": decrypted_key,
        },
        "backendParams": {
            "modelName": flavor.model.model_identifier,
            "temperature": flavor.temperature,
            "top_p": flavor.top_p,
            "maxGenerationLength": max_gen_length,
        },
    }

    try:
        adapter = OpenAIAdapter(task_data)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Provider not configured",
        )

    # 6. Return streaming response
    return StreamingResponse(
        sse_generator(adapter, messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
