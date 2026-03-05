#!/usr/bin/env python3
"""Chat completions endpoint with usage tracking.

Resolves flavor configuration, injects context into the system prompt template,
streams tokens via SSE from the upstream LLM provider, and persists a Job +
FlavorUsage record in a background task for analytics.

When a session_id is provided, token usage is accumulated into a single Job
across all messages in that chat session.
"""

import json
import logging
import time
import uuid
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from app.api.dependencies import get_db
from app.backends.openai_adapter import OpenAIAdapter
from app.core.database import get_standalone_session
from app.models.job import Job
from app.models.model import Model
from app.models.service_flavor import ServiceFlavor
from app.schemas.chat import ChatCompletionRequest, ChatContext
from app.services.flavor_usage_tracker import FlavorUsageTracker
from app.services.provider_service import provider_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class UsageCapture:
    """Mutable container shared between SSE generator and background task."""

    __slots__ = ("usage", "start_time")

    def __init__(self):
        self.usage: dict | None = None
        self.start_time: float = time.monotonic()


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


async def sse_generator(
    adapter: OpenAIAdapter,
    messages: list[dict],
    capture: UsageCapture,
    **kwargs,
):
    """Async generator that yields SSE-formatted events and captures usage."""
    try:
        async for content, usage in adapter.stream_chat(messages, **kwargs):
            if usage:
                capture.usage = usage
                yield f"event: done\ndata: {json.dumps({'usage': usage})}\n\n"
            elif content:
                yield f"event: token\ndata: {json.dumps({'content': content})}\n\n"
    except Exception as e:
        logger.error(f"Chat streaming error: {e}")
        yield f"event: error\ndata: {json.dumps({'error': 'Streaming error'})}\n\n"


async def _persist_chat_metrics(
    capture: UsageCapture,
    service_id: UUID,
    flavor_id: UUID,
    session_id: str | None,
    organization_id: str | None,
    cost_per_1k: float | None,
):
    """Background task: persist or update Job + FlavorUsage after streaming.

    If session_id is provided, looks up an existing Job for that session and
    accumulates token counts. Otherwise creates a new Job per call.
    """
    if not capture.usage:
        logger.debug("Chat completed without usage data, skipping persistence")
        return

    prompt_tokens = capture.usage.get("prompt_tokens", 0)
    completion_tokens = capture.usage.get("completion_tokens", 0)
    total_tokens = prompt_tokens + completion_tokens
    cached_tokens = capture.usage.get("cached_tokens")
    duration_ms = int((time.monotonic() - capture.start_time) * 1000)

    session = get_standalone_session()
    try:
        existing_job = None
        if session_id:
            # Look up existing job for this chat session
            # We store session_id in input_content_preview to correlate
            result = await session.execute(
                select(Job).where(
                    Job.input_content_preview == f"chat:{session_id}",
                    Job.celery_task_id.is_(None),
                )
            )
            existing_job = result.scalar_one_or_none()

        if existing_job:
            # Accumulate tokens into existing job
            prev_metrics = (existing_job.progress or {}).get("token_metrics", {})
            new_prompt = prev_metrics.get("total_prompt_tokens", 0) + prompt_tokens
            new_completion = prev_metrics.get("total_completion_tokens", 0) + completion_tokens
            new_total = new_prompt + new_completion
            new_duration = prev_metrics.get("total_duration_ms", 0) + duration_ms
            message_count = prev_metrics.get("message_count", 0) + 1

            new_cached = prev_metrics.get("total_cached_tokens", 0) + (cached_tokens or 0)

            estimated_cost = None
            if cost_per_1k is not None and new_total > 0:
                estimated_cost = round((new_total / 1000.0) * cost_per_1k, 6)

            updated_metrics = {
                "total_prompt_tokens": new_prompt,
                "total_completion_tokens": new_completion,
                "total_tokens": new_total,
                "total_duration_ms": new_duration,
                "total_estimated_cost": estimated_cost,
                "message_count": message_count,
            }
            if new_cached > 0:
                updated_metrics["total_cached_tokens"] = new_cached

            existing_job.progress = {"token_metrics": updated_metrics}
            existing_job.completed_at = func.now()

            # Record this individual exchange as a FlavorUsage entry
            await FlavorUsageTracker.record_usage(
                db=session,
                flavor_id=flavor_id,
                job_id=existing_job.id,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                latency_ms=duration_ms,
            )

            logger.debug(
                f"Chat metrics accumulated: job={existing_job.id}, "
                f"session={session_id}, total_tokens={new_total}, "
                f"messages={message_count}"
            )
        else:
            # Create new job
            estimated_cost = None
            if cost_per_1k is not None and total_tokens > 0:
                estimated_cost = round((total_tokens / 1000.0) * cost_per_1k, 6)

            token_metrics = {
                "total_prompt_tokens": prompt_tokens,
                "total_completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "total_duration_ms": duration_ms,
                "total_estimated_cost": estimated_cost,
                "message_count": 1,
            }
            if cached_tokens:
                token_metrics["total_cached_tokens"] = cached_tokens

            job_id = uuid.uuid4()
            job = Job(
                id=job_id,
                service_id=service_id,
                flavor_id=flavor_id,
                organization_id=organization_id,
                status="completed",
                celery_task_id=None,
                input_content_preview=f"chat:{session_id}" if session_id else None,
                progress={"token_metrics": token_metrics},
                created_at=func.now(),
                started_at=func.now(),
                completed_at=func.now(),
            )
            session.add(job)
            await session.flush()

            # record_usage commits the session (persists both Job and FlavorUsage)
            await FlavorUsageTracker.record_usage(
                db=session,
                flavor_id=flavor_id,
                job_id=job_id,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                latency_ms=duration_ms,
            )

            logger.debug(
                f"Chat metrics created: job={job_id}, "
                f"session={session_id}, tokens={total_tokens}"
            )
    except Exception:
        await session.rollback()
        logger.exception("Failed to persist chat metrics")
    finally:
        await session.close()


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Stream chat completion tokens via SSE.

    Resolves flavor configuration, builds the system prompt from the template
    and provided context, then streams tokens from the upstream LLM provider.

    - **flavor_id**: UUID of the flavor to use (determines model, provider, prompts)
    - **messages**: Conversation history (user/assistant turns only)
    - **context**: Transcript and optional summary injected into system prompt
    - **max_tokens**: Optional override for max generation length
    - **session_id**: Optional chat session ID to accumulate usage into one Job
    - **organization_id**: Optional organization for cost attribution
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

    # 6. Set up usage capture and background persistence
    capture = UsageCapture()

    background_tasks.add_task(
        _persist_chat_metrics,
        capture,
        flavor.service_id,
        flavor.id,
        request.session_id,
        request.organization_id,
        flavor.estimated_cost_per_1k_tokens,
    )

    # 7. Return streaming response
    return StreamingResponse(
        sse_generator(adapter, messages, capture),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
