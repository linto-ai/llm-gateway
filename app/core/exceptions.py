"""Custom exceptions for LLM Gateway.

This module defines failoverable error types that can trigger automatic
failover to alternative flavors during processing.
"""


class FailoverableError(Exception):
    """Base class for errors that can trigger failover.

    When a flavor fails with one of these errors, the failover chain
    can be used to retry with an alternative flavor if configured.
    """

    def __init__(
        self,
        message: str,
        failover_reason: str,
        original_error: Exception = None
    ):
        super().__init__(message)
        self.failover_reason = failover_reason
        self.original_error = original_error


class TimeoutFailoverError(FailoverableError):
    """Raised when API timeout occurs after retries exhausted.

    This error is raised when the LLM provider API does not respond
    within the configured timeout period, even after retry attempts.
    """

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message, "timeout", original_error)


class RateLimitFailoverError(FailoverableError):
    """Raised when rate limit is exceeded after retries exhausted.

    This error is raised when the LLM provider returns a 429 status
    indicating rate limiting, even after waiting and retry attempts.
    """

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message, "rate_limit", original_error)


class ModelFailoverError(FailoverableError):
    """Raised when model returns error (503, 404, 500, etc.).

    This error is raised when the LLM provider returns a server error
    or indicates the model is unavailable/not found.
    """

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message, "model_error", original_error)


class ContentFilterFailoverError(FailoverableError):
    """Raised when content filter is triggered.

    This error is raised when the LLM provider's content filter blocks
    the request due to policy violations.
    """

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message, "content_filter", original_error)
