from openai import OpenAI, AsyncOpenAI, BadRequestError
import logging
from typing import Optional, Callable, Tuple, Dict
from tenacity import (
    stop_after_attempt, wait_random_exponential,
    retry_if_not_exception_type
)
from app.core.config import settings
import typing


# Type for retry callback: (attempt, max_attempts, delay, error_type, error_message) -> None
RetryCallback = Callable[[int, int, float, str, str], None]

# Type alias for token usage dict returned from API calls
TokenUsage = Dict[str, int]  # {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}


class OpenAIAdapter:
    def __init__(self, task_data: dict, retry_callback: Optional[RetryCallback] = None):
        self.logger = logging.getLogger("OpenAIAdapter")
        self.retry_callback = retry_callback
        self.total_retries = 0

        # Use provider credentials from task_data (required)
        provider_config = task_data.get("providerConfig", {})
        self.api_key = provider_config.get("api_key")
        self.api_base = provider_config.get("api_url")

        if not self.api_key or not self.api_base:
            raise ValueError("Provider config must include api_key and api_url")

        self.modelName = task_data["backendParams"]["modelName"]
        self.temperature = task_data["backendParams"]["temperature"]
        self.top_p = task_data["backendParams"]["top_p"]
        self.maxGenerationLength = task_data["backendParams"]["maxGenerationLength"]

        self.client = OpenAI(api_key=self.api_key, base_url=self.api_base)
        self.async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.api_base)

    def _on_retry(self, retry_state) -> None:
        """Called before each retry attempt. Notifies via callback if configured."""
        self.total_retries += 1
        attempt = retry_state.attempt_number
        max_attempts = settings.api_max_retries

        # Get error info
        exception = retry_state.outcome.exception() if retry_state.outcome else None
        error_type = type(exception).__name__ if exception else "Unknown"
        error_message = str(exception)[:200] if exception else "Unknown error"

        # Calculate delay (already waited, so this is for logging)
        delay = retry_state.idle_for if hasattr(retry_state, 'idle_for') else 0

        self.logger.warning(
            f"LLM API retry {attempt}/{max_attempts}: {error_type} - {error_message[:100]}... "
            f"(waiting {delay:.1f}s)"
        )

        if self.retry_callback:
            try:
                self.retry_callback(attempt, max_attempts, delay, error_type, error_message)
            except Exception as e:
                self.logger.debug(f"Retry callback failed: {e}")


    def _get_retry_decorator(self, exclude_bad_request: bool = True):
        """Create a retry decorator with callback support."""

        kwargs = {
            'wait': wait_random_exponential(min=settings.api_retry_min_delay, max=settings.api_retry_max_delay),
            'stop': stop_after_attempt(settings.api_max_retries),
            'before_sleep': self._on_retry,
        }
        if exclude_bad_request:
            kwargs['retry'] = retry_if_not_exception_type(BadRequestError)

        return kwargs

    def publish(
        self,
        content: str,
        system_prompt: typing.Optional[str] = None,
        temperature: typing.Optional[float] = None,
        top_p: typing.Optional[float] = None,
        max_tokens: typing.Optional[int] = None,
        return_usage: bool = False
        ) -> typing.Union[str, Tuple[str, TokenUsage]]:
        """
        Sync publishes a message to the OpenAI chat model and returns the response.
        Args:
            content (str): The content to be sent to the chat model.
            return_usage (bool): If True, returns (content, usage_dict) tuple.
        Returns:
            str: The response content from the chat model if successful.
            tuple[str, dict]: (content, usage) if return_usage=True.
        Raises:
            BadRequestError: On permanent API errors (not retried)
            Exception: After all retry attempts exhausted
        """
        from tenacity import Retrying

        # Add system prompt if provided
        messages = [{"role": "system", "content": system_prompt}] if system_prompt else []

        # Add user message
        messages.append({"role": "user", "content": content})

        def _call():
            try:
                chat_response = self.client.chat.completions.create(
                    model=self.modelName,
                    messages=messages,
                    temperature=temperature if temperature is not None else self.temperature,
                    top_p=top_p if top_p is not None else self.top_p,
                    max_tokens=max_tokens if max_tokens is not None else self.maxGenerationLength
                )
                response_content = chat_response.choices[0].message.content
                if return_usage and chat_response.usage:
                    usage = {
                        "prompt_tokens": chat_response.usage.prompt_tokens,
                        "completion_tokens": chat_response.usage.completion_tokens,
                        "total_tokens": chat_response.usage.total_tokens,
                    }
                    return response_content, usage
                return response_content
            except BadRequestError as e:
                self.logger.error(f"BadRequestError from API: {e.message}")
                self.logger.error(f"Request params: model={self.modelName}, temp={temperature or self.temperature}, "
                                f"top_p={top_p or self.top_p}, max_tokens={max_tokens or self.maxGenerationLength}")
                self.logger.error(f"Content length: {len(content)} chars")
                raise

        for attempt in Retrying(**self._get_retry_decorator()):
            with attempt:
                return _call()

    async def async_publish(
        self,
        content: str,
        system_prompt: typing.Optional[str] = None,
        temperature: typing.Optional[float] = None,
        top_p: typing.Optional[float] = None,
        max_tokens: typing.Optional[int] = None,
        return_usage: bool = False
        ) -> typing.Union[str, Tuple[str, TokenUsage]]:
        """
        Async publishes a message to the OpenAI chat model and returns the response.
        Args:
            content (str): The content to be sent to the chat model.
            return_usage (bool): If True, returns (content, usage_dict) tuple.
        Returns:
            str: The response content from the chat model if successful.
            tuple[str, dict]: (content, usage) if return_usage=True.
        Raises:
            BadRequestError: On permanent API errors (not retried)
            Exception: After all retry attempts exhausted
        """
        from tenacity import AsyncRetrying

        # Add system prompt if provided
        messages = [{"role": "system", "content": system_prompt}] if system_prompt else []

        # Add user message
        messages.append({"role": "user", "content": content})

        async def _call():
            try:
                chat_response = await self.async_client.chat.completions.create(
                    model=self.modelName,
                    messages=messages,
                    temperature=temperature if temperature is not None else self.temperature,
                    top_p=top_p if top_p is not None else self.top_p,
                    max_tokens=max_tokens if max_tokens is not None else self.maxGenerationLength
                )
                response_content = chat_response.choices[0].message.content
                if return_usage and chat_response.usage:
                    usage = {
                        "prompt_tokens": chat_response.usage.prompt_tokens,
                        "completion_tokens": chat_response.usage.completion_tokens,
                        "total_tokens": chat_response.usage.total_tokens,
                    }
                    return response_content, usage
                return response_content
            except BadRequestError as e:
                self.logger.error(f"BadRequestError from API: {e.message}")
                self.logger.error(f"Request params: model={self.modelName}, temp={temperature or self.temperature}, "
                                f"top_p={top_p or self.top_p}, max_tokens={max_tokens or self.maxGenerationLength}")
                self.logger.error(f"Content length: {len(content)} chars")
                raise

        async for attempt in AsyncRetrying(**self._get_retry_decorator()):
            with attempt:
                return await _call()

    async def generate_title(self, text: str) -> str:
        """Generate a short title for the given text."""
        from tenacity import AsyncRetrying

        messages = [
            {"role": "system", "content": "Please generate a short title for the following text.\n\nBe VERY SUCCINCT. No more than 6 words."},
            {"role": "user", "content": text},
        ]

        async def _call():
            response = await self.async_client.chat.completions.create(
                model=self.modelName,
                messages=messages,
                max_tokens=20,
                temperature=0.5,
            )
            return response.choices[0].message.content.strip()

        async for attempt in AsyncRetrying(**self._get_retry_decorator(exclude_bad_request=False)):
            with attempt:
                return await _call()