#!/usr/bin/env python3
"""Service for testing flavor configurations with live LLM calls."""

from uuid import UUID
from datetime import datetime
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status
from openai import AsyncOpenAI

from app.models.service_flavor import ServiceFlavor
from app.models.model import Model
from app.schemas.flavor_test import FlavorTestRequest, FlavorTestResponse
from app.core.security import get_encryption_service


class FlavorTestService:
    """Service for testing flavor configurations."""

    @staticmethod
    async def test_flavor(
        db: AsyncSession,
        flavor_id: UUID,
        test_request: FlavorTestRequest
    ) -> FlavorTestResponse:
        """
        Execute a test prompt using the flavor configuration.

        Args:
            db: Database session
            flavor_id: ID of the flavor to test
            test_request: Test request with prompt and optional overrides

        Returns:
            FlavorTestResponse: Test execution results with metadata

        Raises:
            HTTPException: If flavor not found, inactive, or inference fails
        """
        # Load flavor with model and provider
        result = await db.execute(
            select(ServiceFlavor)
            .options(
                joinedload(ServiceFlavor.model).joinedload(Model.provider)
            )
            .where(ServiceFlavor.id == flavor_id)
        )
        flavor = result.scalar_one_or_none()

        if not flavor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flavor not found"
            )

        if not flavor.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot test inactive flavor"
            )

        # Extract model and provider info
        model = flavor.model
        provider = model.provider

        # Decrypt provider API key
        api_key = get_encryption_service().decrypt(provider.api_key_encrypted)

        # Determine max_tokens (use override or model's max_generation_length)
        max_tokens = test_request.max_tokens if test_request.max_tokens else model.max_generation_length

        # Build request parameters
        request_params = {
            "prompt": test_request.prompt,
            "temperature": flavor.temperature,
            "max_tokens": max_tokens,
            "top_p": flavor.top_p,
            "frequency_penalty": flavor.frequency_penalty,
            "presence_penalty": flavor.presence_penalty,
            "stop_sequences": flavor.stop_sequences
        }

        # Track start time for latency
        start_time = time.time()

        try:
            # Call LLM API
            client = AsyncOpenAI(
                api_key=api_key,
                base_url=provider.api_base_url
            )

            messages = [{"role": "user", "content": test_request.prompt}]

            # Build API request
            api_kwargs = {
                "model": model.model_identifier,
                "messages": messages,
                "temperature": flavor.temperature,
                "top_p": flavor.top_p,
                "frequency_penalty": flavor.frequency_penalty,
                "presence_penalty": flavor.presence_penalty,
            }

            if max_tokens:
                api_kwargs["max_tokens"] = max_tokens

            if flavor.stop_sequences:
                api_kwargs["stop"] = flavor.stop_sequences

            # Merge custom_params
            if flavor.custom_params:
                api_kwargs.update(flavor.custom_params)

            # Execute LLM call
            response = await client.chat.completions.create(**api_kwargs)

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract response data
            choice = response.choices[0]
            content = choice.message.content
            finish_reason = choice.finish_reason

            # Extract token usage
            usage = response.usage
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens

            # Calculate estimated cost
            estimated_cost = FlavorTestService.calculate_cost(
                input_tokens,
                output_tokens,
                flavor.estimated_cost_per_1k_tokens
            )

            # Build response
            test_response = FlavorTestResponse(
                flavor_id=flavor.id,
                flavor_name=flavor.name,
                model={
                    "model_name": model.model_name,
                    "model_identifier": model.model_identifier,
                    "provider_name": provider.name
                },
                request=request_params,
                response={
                    "content": content,
                    "finish_reason": finish_reason
                },
                metadata={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "latency_ms": latency_ms,
                    "estimated_cost": estimated_cost
                },
                timestamp=datetime.utcnow()
            )

            return test_response

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Model inference failed: {str(e)}"
            )

    @staticmethod
    def calculate_cost(
        input_tokens: int,
        output_tokens: int,
        cost_per_1k: float | None
    ) -> float | None:
        """
        Calculate estimated cost for token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost_per_1k: Cost per 1000 tokens (if known)

        Returns:
            Estimated cost in USD, or None if cost not configured
        """
        if cost_per_1k is None:
            return None

        total_tokens = input_tokens + output_tokens
        return (total_tokens / 1000) * cost_per_1k
