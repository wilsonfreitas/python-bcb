"""Shared HTTP client and utilities for python-bcb."""

from typing import Callable, TypeVar

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
)

# Default timeout for all HTTP requests (seconds)
DEFAULT_TIMEOUT = 30.0

# Shared synchronous HTTP client
_CLIENT = httpx.Client(
    timeout=DEFAULT_TIMEOUT,
    follow_redirects=True,
)

# Shared asynchronous HTTP client (for future async API)
_ASYNC_CLIENT = httpx.AsyncClient(
    timeout=DEFAULT_TIMEOUT,
    follow_redirects=True,
)


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
    return _ASYNC_CLIENT


def close_async_client() -> None:
    """Close the shared async client.

    Call this in long-running applications before shutdown to properly
    close HTTP connections.
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If called from async context, schedule closing
            asyncio.create_task(_ASYNC_CLIENT.aclose())
        else:
            # If called from sync context, run the close
            loop.run_until_complete(_ASYNC_CLIENT.aclose())
    except RuntimeError:
        # No event loop, create one
        asyncio.run(_ASYNC_CLIENT.aclose())


T = TypeVar("T")


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
