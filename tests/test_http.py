"""Shared HTTP error handling tests."""

import asyncio
import ast
from pathlib import Path

import httpx
import pytest

from bcb.exceptions import (
    BCBAPIError,
    BCBAPINotFoundError,
    BCBAPIServerError,
    BCBRateLimitError,
    ODataError,
    SGSError,
)
from bcb import http as http_module
from bcb.http import raise_for_request_error, raise_for_status


def make_response(status_code: int) -> httpx.Response:
    request = httpx.Request("GET", "https://example.test/resource")
    return httpx.Response(status_code, request=request)


def test_raise_for_status_allows_expected_status() -> None:
    raise_for_status(make_response(200), context="Example")


def test_raise_for_status_allows_expected_status_tuple() -> None:
    raise_for_status(make_response(202), context="Example", expected_status=(200, 202))


@pytest.mark.parametrize(
    ("status_code", "error_cls"),
    [
        (429, BCBRateLimitError),
        (404, BCBAPINotFoundError),
        (500, BCBAPIServerError),
    ],
)
def test_raise_for_status_maps_common_http_statuses(
    status_code: int, error_cls: type[BCBAPIError]
) -> None:
    with pytest.raises(error_cls) as exc_info:
        raise_for_status(make_response(status_code), context="Example")

    assert exc_info.value.status_code == status_code


def test_raise_for_status_maps_generic_client_error() -> None:
    with pytest.raises(BCBAPIError) as exc_info:
        raise_for_status(make_response(400), context="Example")

    assert exc_info.value.status_code == 400
    assert "Example" in str(exc_info.value)


def test_raise_for_status_supports_endpoint_specific_exceptions() -> None:
    with pytest.raises(SGSError, match="SGS unavailable"):
        raise_for_status(
            make_response(503),
            context="SGS",
            server_error_cls=SGSError,
            server_error_message="SGS unavailable",
        )


def test_raise_for_status_uses_custom_rate_limit_message() -> None:
    with pytest.raises(BCBRateLimitError, match="Slow down") as exc_info:
        raise_for_status(
            make_response(429),
            context="Example",
            rate_limit_message="Slow down",
        )

    assert exc_info.value.status_code == 429


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectError("connection failed"),
        httpx.TimeoutException("request timed out"),
    ],
)
def test_raise_for_request_error_maps_transport_failures(
    error: httpx.HTTPError,
) -> None:
    with pytest.raises(BCBAPIError) as exc_info:
        raise_for_request_error(error, context="Example")

    assert exc_info.value.status_code == 0
    assert "Example request failed" in str(exc_info.value)


def test_raise_for_request_error_supports_endpoint_specific_exceptions() -> None:
    with pytest.raises(ODataError, match="OData request failed"):
        raise_for_request_error(
            httpx.ConnectError("offline"),
            context="OData",
            error_cls=ODataError,
        )


def test_feature_modules_do_not_import_private_http_clients() -> None:
    private_names = {"_CLIENT", "_ASYNC_CLIENT"}
    violations: list[str] = []
    for module_path in Path("bcb").rglob("*.py"):
        if module_path == Path("bcb/http.py"):
            continue
        tree = ast.parse(module_path.read_text(), filename=str(module_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "bcb.http":
                imported = {alias.name for alias in node.names}
                private_imports = sorted(imported & private_names)
                if private_imports:
                    names = ", ".join(private_imports)
                    violations.append(f"{module_path}: {names}")

    assert violations == []


class FakeAsyncClient:
    def __init__(self, *, is_closed: bool = False) -> None:
        self.is_closed = is_closed
        self.close_count = 0

    async def aclose(self) -> None:
        self.is_closed = True
        self.close_count += 1


def test_get_async_client_recreates_closed_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed_client = FakeAsyncClient(is_closed=True)
    replacement_client = FakeAsyncClient()
    monkeypatch.setattr(http_module, "_ASYNC_CLIENT", closed_client)
    monkeypatch.setattr(http_module, "_make_async_client", lambda: replacement_client)

    assert http_module.get_async_client() is replacement_client


def test_close_async_client_runs_from_sync_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeAsyncClient()
    monkeypatch.setattr(http_module, "_ASYNC_CLIENT", client)

    http_module.close_async_client()

    assert client.is_closed
    assert client.close_count == 1


def test_documented_async_shutdown_example_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeAsyncClient()
    monkeypatch.setattr(http_module, "_ASYNC_CLIENT", client)

    async def main() -> None:
        await http_module.aclose_async_client()

    asyncio.run(main())

    assert client.is_closed
    assert client.close_count == 1


def test_close_async_client_schedules_from_running_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeAsyncClient()
    monkeypatch.setattr(http_module, "_ASYNC_CLIENT", client)

    async def main() -> None:
        http_module.close_async_client()
        await asyncio.sleep(0)

    asyncio.run(main())

    assert client.is_closed
    assert client.close_count == 1


def test_with_retry_decorator_returns_successful_result() -> None:
    calls: list[int] = []

    @http_module.with_retry
    def sample(value: int) -> int:
        calls.append(value)
        return value * 2

    assert sample(21) == 42
    assert calls == [21]
