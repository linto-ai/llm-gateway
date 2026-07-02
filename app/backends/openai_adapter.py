from openai import OpenAI, AsyncOpenAI, BadRequestError
import httpx
import logging
import time
from typing import Optional, Callable, Tuple, Dict
from tenacity import (
    stop_after_attempt, wait_random_exponential,
    retry_if_not_exception_type
)
from app.core.config import settings
import typing


# Type for retry callback: (attempt, max_attempts, delay, error_type, error_message) -> None
RetryCallback = Callable[[int, int, float, str, str], None]

# Provider/model pairs whose client configuration was already logged by this
# process. Batch jobs build one adapter per task, but chat builds one per
# request: without this the "Provider client ready" line would repeat at INFO
# for every chat message.
_LOGGED_CLIENT_CONFIGS: set = set()

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

        # Explicit timeout on every provider call: without it a provider that
        # accepts the connection but never answers blocks the worker forever
        # (job stuck in "started", zero log, zero error). On streaming calls the
        # same value acts as the read timeout between chunks. SDK-internal
        # retries are disabled: tenacity owns the retry policy and logs every
        # attempt (see _get_retry_decorator), silent double-retries would
        # multiply the time a dead provider holds a worker.
        request_timeout = httpx.Timeout(
            settings.provider_request_timeout,
            connect=settings.provider_connect_timeout,
        )
        self.client = OpenAI(
            api_key=self.api_key, base_url=self.api_base,
            timeout=request_timeout, max_retries=0,
        )
        self.async_client = AsyncOpenAI(
            api_key=self.api_key, base_url=self.api_base,
            timeout=request_timeout, max_retries=0,
        )
        config_key = (self.api_base, self.modelName)
        log_config = self.logger.info if config_key not in _LOGGED_CLIENT_CONFIGS else self.logger.debug
        _LOGGED_CLIENT_CONFIGS.add(config_key)
        log_config(
            f"Provider client ready: url={self.api_base} model={self.modelName} "
            f"request_timeout={settings.provider_request_timeout}s "
            f"connect_timeout={settings.provider_connect_timeout}s"
        )

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
            # Propagate the real exception (e.g. APITimeoutError, APIConnectionError)
            # instead of tenacity's opaque RetryError: it ends up verbatim in the
            # job error shown to the user, "Request timed out" beats "RetryError[...]".
            'reraise': True,
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
                self.logger.exception(f"BadRequestError from API: {e.message}")
                self.logger.exception(f"Request params: model={self.modelName}, temp={temperature or self.temperature}, "
                                f"top_p={top_p or self.top_p}, max_tokens={max_tokens or self.maxGenerationLength}")
                self.logger.exception(f"Content length: {len(content)} chars")
                raise

        started = time.monotonic()
        retries_before = self.total_retries
        self.logger.info(
            f"LLM request -> {self.api_base} model={self.modelName} input={len(content)} chars"
        )
        try:
            for attempt in Retrying(**self._get_retry_decorator()):
                with attempt:
                    result = _call()
        except BaseException as e:
            self.logger.error(
                f"LLM request FAILED -> {self.api_base} model={self.modelName} "
                f"after {time.monotonic() - started:.1f}s "
                f"({self.total_retries - retries_before} retries): "
                f"{type(e).__name__}: {str(e)[:200]}"
            )
            raise
        self.logger.info(
            f"LLM response <- {self.api_base} model={self.modelName} "
            f"in {time.monotonic() - started:.1f}s "
            f"({self.total_retries - retries_before} retries)"
        )
        return result

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
                self.logger.exception(f"BadRequestError from API: {e.message}")
                self.logger.exception(f"Request params: model={self.modelName}, temp={temperature or self.temperature}, "
                                f"top_p={top_p or self.top_p}, max_tokens={max_tokens or self.maxGenerationLength}")
                self.logger.exception(f"Content length: {len(content)} chars")
                raise

        started = time.monotonic()
        retries_before = self.total_retries
        self.logger.info(
            f"LLM request -> {self.api_base} model={self.modelName} input={len(content)} chars"
        )
        try:
            async for attempt in AsyncRetrying(**self._get_retry_decorator()):
                with attempt:
                    result = await _call()
        except BaseException as e:
            self.logger.error(
                f"LLM request FAILED -> {self.api_base} model={self.modelName} "
                f"after {time.monotonic() - started:.1f}s "
                f"({self.total_retries - retries_before} retries): "
                f"{type(e).__name__}: {str(e)[:200]}"
            )
            raise
        self.logger.info(
            f"LLM response <- {self.api_base} model={self.modelName} "
            f"in {time.monotonic() - started:.1f}s "
            f"({self.total_retries - retries_before} retries)"
        )
        return result

    async def stream_chat(
        self,
        messages: list[dict],
        **kwargs
    ) -> typing.AsyncGenerator[tuple[str, typing.Optional[TokenUsage]], None]:
        """Stream chat completion tokens.

        Yields tuples of (content_chunk, usage_dict_or_none).
        The last yield has content="" and usage dict from the final chunk.
        No retries: streaming responses cannot be retried mid-stream.

        Args:
            messages: List of message dicts with role and content.
            **kwargs: Optional overrides for temperature, top_p, max_tokens.

        Yields:
            Tuple of (content_string, optional_usage_dict).
        """
        response = await self.async_client.chat.completions.create(
            model=self.modelName,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
            temperature=kwargs.get('temperature', self.temperature),
            top_p=kwargs.get('top_p', self.top_p),
            max_tokens=kwargs.get('max_tokens', self.maxGenerationLength),
        )
        async for chunk in response:
            # Final chunk with usage info
            if chunk.usage:
                usage: TokenUsage = {
                    "prompt_tokens": chunk.usage.prompt_tokens,
                    "completion_tokens": chunk.usage.completion_tokens,
                    "total_tokens": chunk.usage.total_tokens,
                }
                # Track cached tokens if provider reports them
                details = getattr(chunk.usage, "prompt_tokens_details", None)
                if details:
                    cached = getattr(details, "cached_tokens", None)
                    if cached is not None:
                        usage["cached_tokens"] = cached
                yield "", usage
            elif chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content, None

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