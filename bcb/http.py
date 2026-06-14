"""Shared HTTP client and utilities for python-bcb."""

from __future__ import annotations

from typing import Any, Callable, NoReturn, TypeAlias, TypeVar

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
)

from bcb.exceptions import (
    BCBAPIError,
    BCBAPINotFoundError,
    BCBAPIServerError,
    BCBRateLimitError,
)

# Default timeout for all HTTP requests (seconds)
DEFAULT_TIMEOUT = 30.0

RequestTimeout: TypeAlias = float | httpx.Timeout | None

# Shared synchronous HTTP client
_CLIENT = httpx.Client(
    timeout=DEFAULT_TIMEOUT,
    follow_redirects=True,
)


def _make_async_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
    )


# Shared asynchronous HTTP client
_ASYNC_CLIENT = _make_async_client()


# Retry decorator for transient failures
# Retries on any exception (connection errors, timeouts, HTTP 5xx, etc.)
_retry_decorator = retry(
    stop=stop_after_attempt(4),  # 1 initial + 3 retries = 4 attempts
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)


def get_client() -> httpx.Client:
    """Get the shared synchronous HTTP client.

    Returns
    -------
    httpx.Client
        Shared client with connection pooling and configured timeout.
    """
    return _CLIENT


def get_async_client() -> httpx.AsyncClient:
    """Get the shared asynchronous HTTP client.

    Returns
    -------
    httpx.AsyncClient
        Shared async client with connection pooling and configured timeout.
    """
    global _ASYNC_CLIENT
    if _ASYNC_CLIENT.is_closed:
        _ASYNC_CLIENT = _make_async_client()
    return _ASYNC_CLIENT


async def aclose_async_client() -> None:
    """Close the shared async client from async code."""
    if not _ASYNC_CLIENT.is_closed:
        await _ASYNC_CLIENT.aclose()


def close_async_client() -> None:
    """Close the shared async client.

    Call this in long-running applications before shutdown to properly
    close HTTP connections.
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(aclose_async_client())
    else:
        loop.create_task(aclose_async_client())


def timeout_kwargs(timeout: RequestTimeout) -> dict[str, Any]:
    """Build request kwargs without overriding the client default timeout."""
    if timeout is None:
        return {}
    return {"timeout": timeout}


T = TypeVar("T")


def _raise_error(
    error_cls: type[Exception],
    message: str,
    status_code: int,
) -> NoReturn:
    """Raise project exceptions with or without an HTTP status constructor."""
    if issubclass(error_cls, BCBAPIError):
        raise error_cls(message, status_code)
    raise error_cls(message)


def raise_for_status(
    response: httpx.Response,
    *,
    context: str,
    expected_status: int | tuple[int, ...] = 200,
    error_cls: type[Exception] = BCBAPIError,
    not_found_cls: type[Exception] = BCBAPINotFoundError,
    rate_limit_cls: type[Exception] = BCBRateLimitError,
    server_error_cls: type[Exception] = BCBAPIServerError,
    rate_limit_message: str | None = None,
    not_found_message: str | None = None,
    server_error_message: str | None = None,
    error_message: str | None = None,
) -> None:
    """Raise a consistent project exception for unexpected HTTP statuses."""
    expected = (
        (expected_status,) if isinstance(expected_status, int) else expected_status
    )
    status_code = response.status_code
    if status_code in expected:
        return

    if status_code == 429:
        message = (
            rate_limit_message or "BCB API rate limit exceeded. Please try again later."
        )
        _raise_error(rate_limit_cls, message, status_code)
    if status_code == 404:
        message = not_found_message or f"{context} not found (status 404)"
        _raise_error(not_found_cls, message, status_code)
    if status_code >= 500:
        message = (
            server_error_message or f"{context} server error (status {status_code})"
        )
        _raise_error(server_error_cls, message, status_code)

    message = error_message or f"{context} request failed with status {status_code}"
    _raise_error(error_cls, message, status_code)


def raise_for_request_error(
    exc: httpx.HTTPError,
    *,
    context: str,
    error_cls: type[Exception] = BCBAPIError,
) -> NoReturn:
    """Raise a consistent project exception for HTTP client failures."""
    _raise_error(error_cls, f"{context} request failed: {exc}", status_code=0)


def with_retry(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to add automatic retry with exponential backoff to any function.

    Parameters
    ----------
    func : Callable
        Function to retry on failure.

    Returns
    -------
    Callable
        Wrapped function with automatic retry logic.
    """
    return _retry_decorator(func)
